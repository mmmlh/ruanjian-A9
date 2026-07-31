const UTC_TIMESTAMP_PATTERN = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,6}))?)?(Z|[+-]\d{2}:\d{2})?$/

function pad2(value: number): string {
  return value < 10 ? `0${value}` : `${value}`
}

function normalizeUtcInput(value: string): string {
  let input = value.trim()
  if (!input) {
    return ''
  }

  let utcTimestamp = input.match(UTC_TIMESTAMP_PATTERN)
  if (utcTimestamp) {
    let milliseconds = utcTimestamp[7]
      ? `.${(utcTimestamp[7] + '000').substring(0, 3)}`
      : ''
    return `${utcTimestamp[1]}-${utcTimestamp[2]}-${utcTimestamp[3]}T`
      + `${utcTimestamp[4]}:${utcTimestamp[5]}:${utcTimestamp[6] || '00'}${milliseconds}${utcTimestamp[8] || 'Z'}`
  }
  return input
}

function parseUtc(value: string): Date | null {
  let input = value.trim()
  if (!input) {
    return null
  }

  let utcTimestamp = input.match(UTC_TIMESTAMP_PATTERN)
  if (!utcTimestamp) {
    return null
  }

  let normalized = normalizeUtcInput(input)
  let parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  let wallTimestamp = `${utcTimestamp[1]}-${utcTimestamp[2]}-${utcTimestamp[3]}T`
    + `${utcTimestamp[4]}:${utcTimestamp[5]}:${utcTimestamp[6] || '00'}Z`
  let wallTime = new Date(wallTimestamp)
  if (Number.isNaN(wallTime.getTime())
    || wallTime.getUTCFullYear() !== Number(utcTimestamp[1])
    || wallTime.getUTCMonth() + 1 !== Number(utcTimestamp[2])
    || wallTime.getUTCDate() !== Number(utcTimestamp[3])
    || wallTime.getUTCHours() !== Number(utcTimestamp[4])
    || wallTime.getUTCMinutes() !== Number(utcTimestamp[5])
    || wallTime.getUTCSeconds() !== Number(utcTimestamp[6] || '0')) {
    return null
  }
  return parsed
}

export function formatUtcTimestamp(value: string, fallback: string = ''): string {
  if (!value || !value.trim()) {
    return fallback
  }

  let parsed = parseUtc(value)
  if (!parsed) {
    return value
  }
  return `${pad2(parsed.getUTCMonth() + 1)}-${pad2(parsed.getUTCDate())} ${formatUtcClock(parsed)}`
}

export function formatUtcClock(value: Date): string {
  return `${pad2(value.getUTCHours())}:${pad2(value.getUTCMinutes())} UTC`
}

export function toUtcApiTimestamp(value: Date): string {
  return `${value.getUTCFullYear()}-${pad2(value.getUTCMonth() + 1)}-${pad2(value.getUTCDate())} ${pad2(value.getUTCHours())}:${pad2(value.getUTCMinutes())}:${pad2(value.getUTCSeconds())}`
}
