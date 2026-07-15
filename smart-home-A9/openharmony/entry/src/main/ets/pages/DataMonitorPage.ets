import { getDevicesForUi, getSensorHistory, getDeviceLogs } from '../common/ApiClient'
import { Device, parseDeviceStatus, SensorDataItem, LogItem } from '../model/DeviceModel'
import { UiText } from '../common/UiText'
import { ControlCenterTheme } from '../common/ControlCenterTheme'

const PAGE_BG: string = ControlCenterTheme.pageBg
const HERO_BG: string = ControlCenterTheme.surface
const CARD_BG: string = ControlCenterTheme.surface
const PRIMARY: string = ControlCenterTheme.accent
const POSITIVE: string = ControlCenterTheme.accent
const TEXT_PRIMARY: string = ControlCenterTheme.textPrimary
const TEXT_SECONDARY: string = ControlCenterTheme.textSecondary
const SEPARATOR: string = ' 路 '
const DEGREE: string = '掳C'

function localizeMessage(message: string, fallback: string): string {
  if (!message) {
    return fallback
  }
  if (/[\u4e00-\u9fff]/.test(message)) {
    return message
  }
  let transportMessage = UiText.mapTransportMessage(message)
  return transportMessage !== message ? transportMessage : fallback
}

@Entry
@Component
struct DataMonitorPage {
  @State sensors: Device[] = []
  @State sdata: SensorDataItem[] = []
  @State logs: LogItem[] = []
  @State tab: number = 0
  @State curId: number = 0
  @State historyHours: number = 24
  @State loading: boolean = false
  @State historyLoading: boolean = false
  @State logsLoading: boolean = false
  @State errorMessage: string = ''

  aboutToAppear(): void {
    this.load()
  }

  async load(): Promise<void> {
    this.loading = true
    this.errorMessage = ''
    try {
      await this.loadSensors()
      this.sdata = await getSensorHistory(undefined, 60, this.historyStart())
      this.logs = await getDeviceLogs(undefined, 40)
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '加载监测数据失败')
    } finally {
      this.loading = false
    }
  }

  async loadSensors(): Promise<void> {
    let devices = await getDevicesForUi()
    let sensors: Device[] = []
    for (let i = 0; i < devices.length; i++) {
      if (devices[i].type.indexOf('sensor') >= 0) {
        sensors.push(devices[i])
      }
    }
    this.sensors = sensors
  }

  async refresh(): Promise<void> {
    this.errorMessage = ''
    try {
      if (this.tab === 1) {
        this.historyLoading = true
        this.sdata = await getSensorHistory(this.curId > 0 ? this.curId : undefined, 60, this.historyStart())
        return
      }
      if (this.tab === 2) {
        this.logsLoading = true
        this.logs = await getDeviceLogs(this.curId > 0 ? this.curId : undefined, 40)
        return
      }
      await this.loadSensors()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '刷新监测数据失败')
    } finally {
      this.historyLoading = false
      this.logsLoading = false
    }
  }

  lb(dataType: string): string {
    if (dataType === 'temperature') return '温度'
    if (dataType === 'humidity') return '湿度'
    if (dataType === 'presence') return '存在状态'
    return '人体活动'
  }

  un(dataType: string): string {
    if (dataType === 'temperature' || dataType === 'temperature_sensor') return DEGREE
    if (dataType === 'humidity' || dataType === 'humidity_sensor') return '%'
    return ''
  }

  ic(deviceType: string): string {
    if (deviceType === 'temperature' || deviceType === 'temperature_sensor') return '\uD83C\uDF21\uFE0F'
    if (deviceType === 'humidity' || deviceType === 'humidity_sensor') return '\uD83D\uDCA7'
    return '\uD83D\uDC63'
  }

  dn(id: number): string {
    for (let i = 0; i < this.sensors.length; i++) {
      if (this.sensors[i].id === id) return this.sensors[i].name
    }
    return '#' + id.toString()
  }

  tm(ts: string): string {
    if (!ts || ts.length < 16) return ts
    return ts.substring(5, 16)
  }

  historyStart(): string {
    let cutoff = new Date(new Date().getTime() - this.historyHours * 60 * 60 * 1000)
    return this.apiTime(cutoff)
  }

  apiTime(value: Date): string {
    let month = value.getMonth() + 1
    let day = value.getDate()
    let hour = value.getHours()
    let minute = value.getMinutes()
    let second = value.getSeconds()
    let monthText = month < 10 ? '0' + month.toString() : month.toString()
    let dayText = day < 10 ? '0' + day.toString() : day.toString()
    let hourText = hour < 10 ? '0' + hour.toString() : hour.toString()
    let minuteText = minute < 10 ? '0' + minute.toString() : minute.toString()
    let secondText = second < 10 ? '0' + second.toString() : second.toString()
    return value.getFullYear().toString() + '-' + monthText + '-' + dayText + ' ' + hourText + ':' + minuteText + ':' + secondText
  }

  historySummary(): string {
    if (this.sdata.length === 0) {
      return ''
    }
    let latest = this.sdata[0]
    if (this.curId === 0 || this.sdata.length === 1) {
      return '最近 ' + this.historyHours.toString() + ' 小时共 ' + this.sdata.length.toString() + ' 条采样'
    }
    let earliest = this.sdata[this.sdata.length - 1]
    let delta = latest.value - earliest.value
    let sign = delta > 0 ? '+' : ''
    return '最新 ' + latest.value.toFixed(1) + this.un(latest.data_type) + '，较起始 ' + sign + delta.toFixed(1) + this.un(latest.data_type)
  }

  historyInsight(): string {
    for (let index = 0; index < this.sdata.length; index++) {
      let item = this.sdata[index]
      if ((item.data_type === 'humidity' || item.data_type === 'humidity_sensor') && item.value < 40) {
        return '湿度偏低：当前低于 40%，建议检查加湿器或通风状态。'
      }
      if ((item.data_type === 'temperature' || item.data_type === 'temperature_sensor') && item.value > 28) {
        return '温度偏高：当前高于 28°C，建议检查空调或通风状态。'
      }
    }
    return ''
  }

  al(action: string): string {
    switch (action) {
      case 'on': return '开启'
      case 'off': return '关闭'
      case 'set': return '调整参数'
      case 'unlock': return '解锁'
      case 'lock': return '上锁'
      case 'open': return '打开'
      case 'close': return '关闭'
      case 'encrypted': return '加密操作'
      default:
        if (/[\u4e00-\u9fff]/.test(action)) {
          return action
        }
        return '已执行操作'
    }
  }

  localizeTitle(title: string, eventType: string): string {
    if (!title) {
      return eventType === 'scene' ? '场景事件' : '设备操作'
    }
    if (/[\u4e00-\u9fff]/.test(title)) {
      return title
    }
    if (title === 'Home Mode') return '回家模式'
    if (title === 'Away Mode') return '离家模式'
    if (title === 'Sleep Mode') return '睡眠模式'
    if (title === 'Executed scene' || title === 'Scene executed') return '场景已执行'
    return eventType === 'scene' ? '场景事件' : title
  }

  detailLabel(key: string): string {
    switch (key) {
      case 'mode': return '模式'
      case 'temp': return '温度'
      case 'brightness': return '亮度'
      case 'position': return '开合度'
      case 'level': return '档位'
      case 'target_humidity': return '目标湿度'
      case 'power_watts': return '功率'
      case 'total_kwh': return '累计耗电'
      default: return key
    }
  }

  stringifyValue(value: Object | undefined | null): string {
    if (value === undefined || value === null) return ''
    if (typeof value === 'string') return value as string
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value)
    } catch (err) {
      return ''
    }
  }

  formatLogDetail(item: LogItem): string {
    if (!item.detail) {
      return '指令执行成功'
    }
    try {
      let parsed = JSON.parse(item.detail) as Record<string, Object>
      let values: string[] = []
      let keys = Object.keys(parsed)
      for (let i = 0; i < keys.length; i++) {
        let key = keys[i]
        if (key === 'action') continue
        let value = this.stringifyValue(parsed[key])
        if (!value) continue
        if (key === 'temp') {
          value = value + DEGREE
        } else if (key === 'brightness' || key === 'position' || key === 'level' || key === 'target_humidity') {
          value = value + '%'
        } else if (key === 'power_watts') {
          value = value + 'W'
        } else if (key === 'total_kwh') {
          value = value + 'kWh'
        }
        values.push(this.detailLabel(key) + ': ' + value)
      }
      if (values.length > 0) {
        return values.join(SEPARATOR)
      }
    } catch (err) {
    }
    return /[\u4e00-\u9fff]/.test(item.detail) ? item.detail : '日志详情已更新'
  }

  logHeadline(item: LogItem): string {
    let title = this.localizeTitle(item.title || this.al(item.action), item.event_type)
    if (item.event_type && item.event_type !== 'device') {
      return title
    }
    if (item.device_id > 0) {
      return title + SEPARATOR + this.dn(item.device_id)
    }
    return title
  }

  liveValue(device: Device): string {
    let status = parseDeviceStatus(device.status_json)
    if (device.type === 'pir_sensor') {
      return status.presence ? '检测到活动' : '区域空闲'
    }
    return status.value + this.un(device.type)
  }

  build() {
    Column() {
      if (this.loading) {
        this.buildLoading()
      } else {
        Scroll() {
          Column() {
            this.buildTopBar()
            this.buildFeedback()
            this.buildHero()
            this.buildTabs()
            if (this.tab === 0) {
              this.buildLivePanel()
            } else if (this.tab === 1) {
              this.buildHistoryPanel()
            } else {
              this.buildLogsPanel()
            }
          }
          .padding({ left: 16, right: 16, top: 16, bottom: 24 })
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(PAGE_BG)
  }

  @Builder buildTopBar() {
    Row() {
      Text('\u2190').fontSize(20).fontColor(TEXT_PRIMARY).padding(8).onClick(() => this.getUIContext().getRouter().back())
      Text('数据监测').fontSize(18).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY).margin({ left: 6 })
      Blank()
      Text('刷新').fontSize(12).fontColor(PRIMARY).fontWeight(FontWeight.Bold).onClick(() => this.refresh())
    }
    .width('100%')
  }

  @Builder buildFeedback() {
    if (this.errorMessage) {
      Text(this.errorMessage)
        .fontSize(13)
        .fontColor('#A04444')
        .padding({ left: 14, right: 14, top: 10, bottom: 10 })
        .borderRadius(14)
        .backgroundColor('#FBE3E3')
        .width('100%')
        .margin({ top: 14 })
    }
  }

  @Builder buildHero() {
    Row() {
      Column() {
        Text('监测工作台').fontSize(22).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY)
        Text('实时遥测、历史记录与运行日志').fontSize(12).fontColor(TEXT_SECONDARY).margin({ top: 6 })
      }
      .alignItems(HorizontalAlign.Start)
      Blank()
      Column() {
        Text(this.sensors.length.toString()).fontSize(30).fontWeight(FontWeight.Bold).fontColor(POSITIVE)
        Text('传感节点').fontSize(12).fontColor(TEXT_SECONDARY).margin({ top: 4 })
      }
      .alignItems(HorizontalAlign.End)
    }
    .width('100%')
    .padding(20)
    .borderRadius(ControlCenterTheme.radiusHero)
    .backgroundColor(HERO_BG)
    .border({ width: 1, color: ControlCenterTheme.border })
    .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
    .margin({ top: 16 })
  }

  @Builder buildTabs() {
    Row() {
      this.tabChip('实时数据', this.tab === 0, () => { this.tab = 0 })
      this.tabChip('历史记录', this.tab === 1, () => { this.tab = 1; this.refresh() })
      this.tabChip('运行日志', this.tab === 2, () => { this.tab = 2; this.refresh() })
    }
    .width('100%')
    .margin({ top: 16 })
  }

  @Builder tabChip(label: string, active: boolean, action: () => void) {
    Text(label)
      .fontSize(12)
      .fontWeight(active ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(active ? '#FFFFFF' : TEXT_SECONDARY)
      .padding({ left: 18, right: 18, top: 10, bottom: 10 })
      .borderRadius(14)
      .backgroundColor(active ? PRIMARY : CARD_BG)
      .margin({ right: 8 })
      .onClick(action)
  }

  @Builder buildLivePanel() {
    if (this.sensors.length === 0) {
      this.buildEmptyState('暂未绑定传感设备', '请先绑定传感设备后再查看实时数据')
    } else {
      GridRow({ columns: 2, gutter: 12 }) {
        ForEach(this.sensors, (device: Device) => {
          GridCol() {
            Column() {
              Row() {
                Column() {
                  Text(this.ic(device.type)).fontSize(22)
                }
                .width(44)
                .height(44)
                .borderRadius(16)
                .backgroundColor('#F4F7FA')
                .justifyContent(FlexAlign.Center)
                .alignItems(HorizontalAlign.Center)
                Blank()
              }
              .width('100%')

              Text(device.name).fontSize(15).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY).margin({ top: 14 })
              Text(this.liveValue(device)).fontSize(28).fontWeight(FontWeight.Bold).fontColor(PRIMARY).margin({ top: 8 })
              Text(device.room_name || '传感节点').fontSize(11).fontColor(TEXT_SECONDARY).margin({ top: 6 })
            }
            .padding(16)
            .borderRadius(22)
            .backgroundColor(CARD_BG)
          }
        }, (device: Device) => device.id.toString())
      }
      .margin({ top: 16 })
    }
  }

  @Builder buildHistoryPanel() {
    if (this.historyLoading) {
      this.buildSectionLoading('正在刷新历史记录...')
    } else {
      Column() {
        Scroll() {
          Row() {
            this.filterChip('全部传感器', this.curId === 0, () => { this.curId = 0; this.refresh() })
            ForEach(this.sensors, (device: Device) => {
              this.filterChip(device.name, this.curId === device.id, () => { this.curId = device.id; this.refresh() })
            }, (device: Device) => device.id.toString())
          }
        }
        .scrollable(ScrollDirection.Horizontal)
        .scrollBar(BarState.Off)
        .width('100%')

        Row() {
          this.rangeChip('24小时', this.historyHours === 24, () => { this.historyHours = 24; this.refresh() })
          this.rangeChip('7天', this.historyHours === 168, () => { this.historyHours = 168; this.refresh() })
        }
        .width('100%')
        .margin({ top: 12 })

        if (this.sdata.length === 0) {
          this.buildEmptyState('暂无历史记录', '历史传感器记录会显示在这里')
        } else {
          Column() {
            Text(this.historySummary())
              .fontSize(12)
              .fontColor(TEXT_SECONDARY)
              .width('100%')
              .margin({ top: 14, bottom: 2 })
            if (this.historyInsight()) {
              Text(this.historyInsight())
                .fontSize(12)
                .fontColor('#9A651D')
                .width('100%')
                .padding({ left: 12, right: 12, top: 10, bottom: 10 })
                .borderRadius(14)
                .backgroundColor(ControlCenterTheme.warningSoft)
                .margin({ top: 10 })
            }
            ForEach(this.sdata.slice(0, 50), (item: SensorDataItem) => {
              Row() {
                Column() {
                  Text(this.lb(item.data_type)).fontSize(14).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY)
                  Text(this.dn(item.device_id)).fontSize(11).fontColor(TEXT_SECONDARY).margin({ top: 4 })
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)

                Column() {
                  Text(item.value.toFixed(1) + this.un(item.data_type)).fontSize(20).fontWeight(FontWeight.Bold).fontColor(PRIMARY)
                  Text(this.tm(item.timestamp)).fontSize(10).fontColor('#98A2AD').margin({ top: 4 })
                }
                .alignItems(HorizontalAlign.End)
              }
              .width('100%')
              .padding({ left: 16, right: 16, top: 14, bottom: 14 })
              .borderRadius(18)
              .backgroundColor(CARD_BG)
              .margin({ top: 10 })
            }, (item: SensorDataItem) => item.id.toString())
          }
        }
      }
      .width('100%')
      .margin({ top: 16 })
    }
  }

  @Builder buildLogsPanel() {
    if (this.logsLoading) {
      this.buildSectionLoading('正在刷新日志...')
    } else if (this.logs.length === 0) {
      this.buildEmptyState('暂无操作日志', '设备与自动化日志会显示在这里')
    } else {
      Column() {
        ForEach(this.logs.slice(0, 40), (item: LogItem) => {
          Row() {
            Column() {
              Text(this.logHeadline(item)).fontSize(14).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY)
              if (item.detail) {
                Text(this.formatLogDetail(item))
                  .fontSize(11)
                  .fontColor(TEXT_SECONDARY)
                  .margin({ top: 5 })
                  .maxLines(1)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
            }
            .layoutWeight(1)
            .alignItems(HorizontalAlign.Start)

            Text(this.tm(item.timestamp)).fontSize(11).fontColor('#98A2AD')
          }
          .width('100%')
          .padding({ left: 16, right: 16, top: 14, bottom: 14 })
          .borderRadius(18)
          .backgroundColor(CARD_BG)
          .margin({ top: 10 })
        }, (item: LogItem) => (item.source || item.event_type || 'log') + ':' + item.id.toString())
      }
      .width('100%')
      .margin({ top: 16 })
    }
  }

  @Builder filterChip(label: string, active: boolean, action: () => void) {
    Text(label)
      .fontSize(12)
      .fontWeight(active ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(active ? '#FFFFFF' : TEXT_SECONDARY)
      .padding({ left: 16, right: 16, top: 10, bottom: 10 })
      .borderRadius(14)
      .backgroundColor(active ? PRIMARY : CARD_BG)
      .margin({ right: 8 })
      .onClick(action)
  }

  @Builder rangeChip(label: string, active: boolean, action: () => void) {
    Text(label)
      .fontSize(12)
      .fontWeight(active ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(active ? '#FFFFFF' : TEXT_SECONDARY)
      .padding({ left: 16, right: 16, top: 10, bottom: 10 })
      .borderRadius(14)
      .backgroundColor(active ? PRIMARY : ControlCenterTheme.surfaceMuted)
      .margin({ right: 8 })
      .onClick(action)
  }

  @Builder buildEmptyState(title: string, subtitle: string) {
    Column() {
      Text(title).fontSize(15).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY)
      Text(subtitle).fontSize(12).fontColor(TEXT_SECONDARY).margin({ top: 6 })
    }
    .width('100%')
    .padding({ top: 28, bottom: 28 })
    .borderRadius(22)
    .backgroundColor(CARD_BG)
    .alignItems(HorizontalAlign.Center)
    .margin({ top: 16 })
  }

  @Builder buildSectionLoading(label: string) {
    Column() {
      LoadingProgress().width(30).height(30).color(PRIMARY)
      Text(label).fontSize(13).fontColor(TEXT_SECONDARY).margin({ top: 12 })
    }
    .width('100%')
    .padding({ top: 28, bottom: 28 })
    .borderRadius(22)
    .backgroundColor(CARD_BG)
    .alignItems(HorizontalAlign.Center)
    .margin({ top: 16 })
  }

  @Builder buildLoading() {
    Column() {
      LoadingProgress().width(34).height(34).color(PRIMARY)
      Text('正在加载监测工作台...').fontSize(13).fontColor(TEXT_SECONDARY).margin({ top: 14 })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }
}
