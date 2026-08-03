import { getDashboardSummary, executeScene } from '../common/ApiClient'
import { connectWS, disconnectWS } from '../common/MqttClient'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { AppTopBar, AppBottomNav, SectionTitle, StatusBanner } from '../common/ControlCenterKit'
import { UiText } from '../common/UiText'
import { formatUtcClock, formatUtcTimestamp } from '../common/UtcTimeUtil'
import { Room, Device, Scene, LogItem, parseDeviceStatus } from '../model/DeviceModel'

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

class DashboardHelper {
  static icon(type: string): string {
    switch (type) {
      case 'light': return '灯'
      case 'ac': return '空'
      case 'door_lock': return '锁'
      case 'temperature_sensor': return '温'
      case 'humidity_sensor': return '湿'
      case 'pir_sensor': return '人'
      case 'curtain': return '帘'
      case 'humidifier': return '雾'
      default: return '设'
    }
  }

  static localizeSummary(summary: string): string {
    if (!summary) {
      return summary
    }
    if (/[\u4e00-\u9fff]/.test(summary)) {
      return summary
    }
    if (summary === 'Offline') return '设备离线'
    if (summary === 'Power off') return '已关闭'
    if (summary === 'Standby') return '待机中'
    if (summary === 'Securely locked') return '门锁已上锁'
    if (summary === 'Unlocked') return '门锁已解锁'
    if (summary === 'Fully closed') return '已完全关闭'
    if (summary === 'Motion detected') return '检测到活动'
    if (summary === 'Area idle') return '区域静止'
    if (summary.indexOf('Brightness ') === 0) {
      return '亮度 ' + summary.substring('Brightness '.length)
    }
    if (summary.indexOf('Cooling ') === 0) {
      return '制冷 ' + summary.substring('Cooling '.length)
    }
    if (summary.indexOf('Open ') === 0) {
      return '开合 ' + summary.substring('Open '.length)
    }
    if (summary.indexOf('Humidity target ') === 0) {
      return '目标湿度 ' + summary.substring('Humidity target '.length)
    }
    return summary
  }

  static status(device: Device): string {
    if (!device.online) {
      if (device.status_summary) {
        return '离线 · ' + DashboardHelper.localizeSummary(device.status_summary)
      }
      return '离线'
    }
    if (device.status_summary) {
      return DashboardHelper.localizeSummary(device.status_summary)
    }
    let status = parseDeviceStatus(device.status_json)
    switch (device.type) {
      case 'light':
        return status.power === 'on' ? '亮度 ' + status.brightness + '%' : '已关闭'
      case 'ac':
        return status.power === 'on' ? '制冷 ' + status.temp + '°C' : '待机中'
      case 'door_lock':
        return status.locked ? '门锁已上锁' : '门锁已解锁'
      case 'curtain':
        return status.position > 0 ? '开合 ' + status.position + '%' : '已完全关闭'
      case 'humidifier':
        return status.power === 'on' ? '目标湿度 ' + status.target_humidity + '%' : '已关闭'
      case 'temperature_sensor':
        return status.value + '°C'
      case 'humidity_sensor':
        return status.value + '%'
      case 'pir_sensor':
        return status.presence ? '检测到活动' : '区域静止'
      default:
        return '--'
    }
  }

  static logLabel(item: LogItem): string {
    switch (item.action) {
      case 'on': return '已开启'
      case 'off': return '已关闭'
      case 'set': return '已调整'
      case 'unlock': return '已解锁'
      case 'lock': return '已上锁'
      case 'open': return '已打开'
      case 'close': return '已关闭'
      case 'encrypted': return '已发送加密指令'
      default:
        if (/[\u4e00-\u9fff]/.test(item.action)) {
          return item.action
        }
        return '已执行操作'
    }
  }

  static sceneName(name: string): string {
    switch (name) {
      case 'Home Mode': return '回家模式'
      case 'Away Mode': return '离家模式'
      case 'Sleep Mode': return '睡眠模式'
      default: return name
    }
  }

  static sceneDescription(description: string): string {
    if (!description) {
      return '一键执行常用的联动场景。'
    }
    if (/[\u4e00-\u9fff]/.test(description)) {
      return description
    }
    if (description === 'Executed scene' || description === 'Scene executed') {
      return '场景执行完成'
    }
    return description
  }

  static localizeFreeformText(text: string, fallback: string): string {
    if (!text) {
      return fallback
    }
    if (/[\u4e00-\u9fff]/.test(text)) {
      return text
    }
    if (text === 'Executed scene' || text === 'Scene executed') {
      return '场景执行完成'
    }
    if (text.indexOf('command dispatched') >= 0) {
      return '设备指令已下发'
    }
    return text
  }

  static stringifyValue(value: Object | undefined | null): string {
    if (value === undefined || value === null) {
      return ''
    }
    if (typeof value === 'string') {
      return value as string
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return String(value)
    }
    try {
      return JSON.stringify(value)
    } catch (err) {
      return ''
    }
  }

  static detailLabel(key: string): string {
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

  static formatDetail(item: LogItem): string {
    if (!item.detail) {
      return '指令执行成功'
    }

    try {
      let parsed = JSON.parse(item.detail) as Record<string, Object>
      let values: string[] = []
      let keys = Object.keys(parsed)
      for (let i = 0; i < keys.length; i++) {
        let key = keys[i]
        if (key === 'action') {
          continue
        }
        let value = DashboardHelper.stringifyValue(parsed[key])
        if (!value) {
          continue
        }
        let label = DashboardHelper.detailLabel(key)
        if (key === 'temp') {
          value = value + '°C'
        } else if (key === 'brightness' || key === 'position' || key === 'level' || key === 'target_humidity') {
          value = value + '%'
        } else if (key === 'power_watts') {
          value = value + 'W'
        } else if (key === 'total_kwh') {
          value = value + 'kWh'
        }
        values.push(label + ': ' + value)
      }
      if (values.length > 0) {
        return values.join(' · ')
      }
    } catch (err) {
    }

    return DashboardHelper.localizeFreeformText(item.detail, '操作详情已更新')
  }
}

let SCENE_ICONS: Record<string, string> = {
  'Home Mode': '家',
  'Away Mode': '离',
  'Sleep Mode': '眠',
  '回家模式': '家',
  '离家模式': '离',
  '睡眠模式': '眠'
}

@Entry
@Component
struct DashboardPage {
  @State rooms: Room[] = []
  @State devices: Device[] = []
  @State scenes: Scene[] = []
  @State recentLogs: LogItem[] = []
  @State cur: number = 0
  @State ok: boolean = false
  @State temp: string = '--'
  @State hum: string = '--'
  @State exe: number = -1
  @State loading: boolean = false
  @State errorMessage: string = ''
  @State successMessage: string = ''
  @State onlineCount: number = 0
  @State totalCount: number = 0
  @State lastSynced: string = ''
  @State lastSyncedAt: number = 0
  @State pendingSceneId: number = -1

  aboutToAppear(): void {
    this.ld()
    connectWS((msg: string) => this.ws(msg), (connected: boolean) => {
      this.ok = connected
    })
  }

  aboutToDisappear(): void {
    disconnectWS()
  }

  async ld(): Promise<void> {
    if (this.loading) {
      return
    }
    this.loading = true
    this.errorMessage = ''
    try {
      let summary = await getDashboardSummary()
      this.rooms = summary.rooms
      this.devices = summary.devices
      this.scenes = summary.scenes
      this.recentLogs = summary.recent_logs
      this.onlineCount = summary.stats.online_devices
      this.totalCount = summary.stats.total_devices
      this.syncClimate()
      this.lastSynced = this.syncTime()
      this.lastSyncedAt = new Date().getTime()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '加载全屋总览失败')
    } finally {
      this.loading = false
    }
  }

  syncClimate(): void {
    this.temp = '--'
    this.hum = '--'
    for (let i = 0; i < this.devices.length; i++) {
      let device = this.devices[i]
      let status = parseDeviceStatus(device.status_json)
      if (device.type === 'temperature_sensor') {
        this.temp = status.value.toFixed(1)
      } else if (device.type === 'humidity_sensor') {
        this.hum = status.value.toFixed(0)
      }
    }
  }

  rf(): void {
    this.ld()
  }

  syncTime(): string {
    return formatUtcClock(new Date())
  }

  syncStatusLabel(): string {
    if (!this.lastSynced || this.lastSyncedAt === 0) {
      return '正在获取全屋状态'
    }
    let age = new Date().getTime() - this.lastSyncedAt
    if (age > 5 * 60 * 1000) {
      return '数据可能延迟，请刷新确认'
    }
    if (age > 60 * 1000) {
      return '最后同步 ' + this.lastSynced + ' · 数据可能延迟'
    }
    return '最后同步 ' + this.lastSynced
  }


  flt(roomId: number): Device[] {
    if (roomId === 0) {
      return this.devices
    }
    let filtered: Device[] = []
    for (let i = 0; i < this.devices.length; i++) {
      if (this.devices[i].room_id === roomId) {
        filtered.push(this.devices[i])
      }
    }
    return filtered
  }

  async ds(sceneId: number): Promise<void> {
    if (this.exe >= 0) {
      return
    }
    this.exe = sceneId
    this.errorMessage = ''
    this.successMessage = ''
    try {
      await executeScene(sceneId)
      this.successMessage = '场景执行成功'
      await this.ld()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '场景执行失败')
    } finally {
      this.exe = -1
    }
  }

  parseSceneActions(scene: Scene): Array<Record<string, Object>> {
    let actions: Array<Record<string, Object>> = []
    if (!scene.actions_json) {
      return actions
    }

    try {
      let parsed = JSON.parse(scene.actions_json) as Object
      if (Array.isArray(parsed)) {
        let parsedActions = parsed as Array<Record<string, Object>>
        for (let index = 0; index < parsedActions.length; index++) {
          actions.push(parsedActions[index])
        }
      } else if (parsed !== null && typeof parsed === 'object') {
        actions.push(parsed as Record<string, Object>)
      }
    } catch (err) {
    }
    return actions
  }

  isSafetySensitiveScene(scene: Scene): boolean {
    let actions = this.parseSceneActions(scene)
    for (let index = 0; index < actions.length; index++) {
      let deviceType = DashboardHelper.stringifyValue(actions[index]['device_type']).toLowerCase()
      let action = DashboardHelper.stringifyValue(actions[index]['action']).toLowerCase()
      let sensitiveDevice = deviceType === 'door_lock' || deviceType === 'security' || deviceType === 'alarm'
      let sensitiveAction = action === 'lock' || action === 'unlock' || action === 'arm' || action === 'disarm'
      if (sensitiveDevice || sensitiveAction) {
        return true
      }
    }
    let name = DashboardHelper.sceneName(scene.name)
    return name.indexOf('离家') >= 0 || name.indexOf('安防') >= 0 || name.indexOf('门锁') >= 0 || name.indexOf('锁门') >= 0
  }

  sceneById(sceneId: number): Scene | null {
    for (let index = 0; index < this.scenes.length; index++) {
      if (this.scenes[index].id === sceneId) {
        return this.scenes[index]
      }
    }
    return null
  }

  requestScene(sceneId: number): void {
    if (this.exe >= 0) {
      return
    }
    let scene = this.sceneById(sceneId)
    if (scene !== null && this.isSafetySensitiveScene(scene)) {
      this.pendingSceneId = sceneId
      return
    }
    this.ds(sceneId)
  }

  confirmScene(): void {
    if (this.exe >= 0) {
      return
    }
    let sceneId = this.pendingSceneId
    this.pendingSceneId = -1
    if (sceneId > 0) {
      this.ds(sceneId)
    }
  }

  pendingSceneDescription(): string {
    let scene = this.sceneById(this.pendingSceneId)
    if (scene === null) {
      return '该场景会控制家庭中的安全设备。'
    }
    return '“' + DashboardHelper.sceneName(scene.name) + '”会控制家庭中的安全设备。'
  }

  ws(msg: string): void {
    try {
      let data = JSON.parse(msg) as Record<string, Object>
      if (data['type'] === 'mqtt') {
        let topic = data['topic'] as string
        let payload = data['payload'] as Record<string, Object>
        this.updateDeviceFromRealtime(topic, payload)
      }
    } catch (err) {
      console.error(err)
    }
  }

  updateDeviceFromRealtime(topic: string, payload: Record<string, Object>): void {
    let deviceTopic = this.deviceTopicFromRealtime(topic)
    if (!deviceTopic) {
      return
    }

    let mergedPayload = this.normalizeRealtimePayload(topic, payload)
    if (mergedPayload === null) {
      return
    }

    for (let i = 0; i < this.devices.length; i++) {
      let device = this.devices[i]
      if (device.mqtt_topic !== deviceTopic) {
        continue
      }
      let mergedStatus = this.mergeRealtimeStatus(device.status_json, mergedPayload)
      let replacement = new Device()
      replacement.id = device.id
      replacement.room_id = device.room_id
      replacement.type = device.type
      replacement.name = device.name
      replacement.brand = device.brand
      replacement.mqtt_topic = device.mqtt_topic
      replacement.status_json = device.status_json
      replacement.room_name = device.room_name
      replacement.updated_at = device.updated_at
      replacement.last_seen_at = device.last_seen_at
      replacement.status_summary = device.status_summary
      replacement.online = device.online
      replacement.status_json = JSON.stringify(mergedStatus)
      let now = new Date().toISOString()
      replacement.updated_at = now
      replacement.last_seen_at = now
      replacement.status_summary = ''
      replacement.online = true
      let updatedDevices: Device[] = this.devices.slice()
      updatedDevices[i] = replacement
      this.devices = updatedDevices
      this.syncClimate()
      this.recountOnline()
      return
    }
  }

  deviceTopicFromRealtime(topic: string): string {
    let parts = topic.split('/')
    if (parts.length < 4 || parts[0] !== 'home') {
      return ''
    }
    return parts[0] + '/' + parts[1] + '/' + parts[2]
  }

  normalizeRealtimePayload(topic: string, payload: Record<string, Object>): Record<string, Object> | null {
    let parts = topic.split('/')
    if (parts.length < 4) {
      return null
    }

    let suffix = parts[3]
    let source: Record<string, Object> = payload
    if (suffix === 'response') {
      let state = payload['state']
      if (state === undefined || state === null) {
        return null
      }
      source = state as Record<string, Object>
    } else if (suffix !== 'status' && suffix !== 'sensor') {
      return null
    }

    let normalized: Record<string, Object> = {}
    let keys = Object.keys(source)
    for (let i = 0; i < keys.length; i++) {
      let key = keys[i]
      if (key === 'device_id' || key === 'brand_command' || key === 'success' || key === 'ts') {
        continue
      }
      normalized[key] = source[key]
    }

    if (Object.keys(normalized).length === 0) {
      return null
    }
    return normalized
  }

  mergeRealtimeStatus(statusJson: string, incoming: Record<string, Object>): Record<string, Object> {
    let merged: Record<string, Object> = {}
    try {
      let existing = JSON.parse(statusJson) as Record<string, Object>
      let existingKeys = Object.keys(existing)
      for (let i = 0; i < existingKeys.length; i++) {
        let key = existingKeys[i]
        merged[key] = existing[key]
      }
    } catch (err) {
    }

    let incomingKeys = Object.keys(incoming)
    for (let i = 0; i < incomingKeys.length; i++) {
      let key = incomingKeys[i]
      merged[key] = incoming[key]
    }
    return merged
  }

  recountOnline(): void {
    let online = 0
    for (let i = 0; i < this.devices.length; i++) {
      if (this.devices[i].online) {
        online++
      }
    }
    this.onlineCount = online
    this.totalCount = this.devices.length
  }

  dotColor(device: Device): string {
    if (!device.online) {
      return ControlCenterTheme.borderStrong
    }
    let status = parseDeviceStatus(device.status_json)
    if (device.type === 'light' || device.type === 'ac' || device.type === 'humidifier') {
      return status.power === 'on' ? ControlCenterTheme.success : ControlCenterTheme.accent
    }
    if (device.type === 'door_lock') {
      return status.locked ? ControlCenterTheme.success : ControlCenterTheme.warning
    }
    if (device.type === 'pir_sensor') {
      return status.presence ? ControlCenterTheme.warning : ControlCenterTheme.borderStrong
    }
    return ControlCenterTheme.accent
  }

  sceneIcon(name: string): string {
    let icon = SCENE_ICONS[name]
    if (icon !== undefined && icon !== null) {
      return icon
    }
    return '景'
  }

  shortTime(value: string): string {
    return formatUtcTimestamp(value, value)
  }

  formatLogDetail(item: LogItem): string {
    return DashboardHelper.formatDetail(item)
  }

  roomName(roomId: number): string {
    for (let i = 0; i < this.rooms.length; i++) {
      if (this.rooms[i].id === roomId) {
        return this.rooms[i].name
      }
    }
    return '未分配房间'
  }

  visibleDevices(): Device[] {
    return this.flt(this.cur)
  }

  quickAction(route: string): void {
    try {
      this.getUIContext().getRouter().pushUrl({ url: route })
    } catch (err) {
      this.errorMessage = '页面跳转失败'
      console.error(err)
    }
  }

  offlineCount(): number {
    return this.totalCount > this.onlineCount ? this.totalCount - this.onlineCount : 0
  }

  build() {
    Column() {
      AppTopBar({ title: '我的家', subtitle: this.syncStatusLabel(), actionLabel: '刷新', onAction: () => this.rf() })
        .padding({ left: ControlCenterTheme.gutter, right: ControlCenterTheme.gutter,
          top: ControlCenterTheme.spaceMd, bottom: ControlCenterTheme.spaceSm })
      if (this.loading) {
        this.buildLoading()
      } else {
        Scroll() {
          Column() {
            this.buildMijiaHomeHero()
            this.buildFeedback()
            if (this.pendingSceneId > 0) {
              this.buildSceneConfirmation()
            }
            this.buildMijiaSceneStrip()
            this.buildRoomFilter()
            this.buildDeviceGrid()
            this.buildActivityPanel()
          }
          .padding({ left: ControlCenterTheme.gutter, right: ControlCenterTheme.gutter,
            top: ControlCenterTheme.spaceSm, bottom: ControlCenterTheme.spaceXl })
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)
      }
      AppBottomNav({ active: 'home' })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(ControlCenterTheme.pageBg)
  }

  @Builder buildLoading() {
    Column() {
      LoadingProgress()
        .width(34)
        .height(34)
        .color(ControlCenterTheme.accent)
      Text('正在加载全屋控制台...')
        .fontSize(13)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: 14 })
    }
    .width('100%')
    .layoutWeight(1)
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }

  @Builder buildFeedback() {
    if (this.successMessage) {
      StatusBanner({ message: this.successMessage, detail: '已同步刷新', tone: 'success' })
        .margin({ top: 14 })
    }

    if (this.errorMessage) {
      StatusBanner({ message: this.errorMessage, detail: '请稍后重试', tone: 'danger' })
        .margin({ top: this.successMessage ? 8 : 14 })
    }
  }

  @Builder buildSceneConfirmation() {
    Column() {
      Text('确认执行安全场景')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
      Text(this.pendingSceneDescription())
        .fontSize(12)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: 6 })
        .width('100%')
      Row() {
        Button('取消')
          .layoutWeight(1)
          .height(ControlCenterTheme.controlHeight)
          .backgroundColor(ControlCenterTheme.surfaceMuted)
          .fontColor(ControlCenterTheme.textPrimary)
          .borderRadius(ControlCenterTheme.radiusInner)
          .onClick(() => { this.pendingSceneId = -1 })
        Blank().width(10)
        Button('确认执行')
          .layoutWeight(1)
          .height(ControlCenterTheme.controlHeight)
          .backgroundColor(ControlCenterTheme.accent)
          .fontColor(ControlCenterTheme.surface)
          .borderRadius(ControlCenterTheme.radiusInner)
          .enabled(this.exe < 0)
          .onClick(() => this.confirmScene())
      }
      .width('100%')
      .margin({ top: 14 })
    }
    .width('100%')
    .padding(16)
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(ControlCenterTheme.warningSoft)
    .margin({ top: 14 })
  }

  @Builder buildMijiaHomeHero() {
    Column() {
      Text('全屋状态')
        .fontSize(12)
        .fontColor(ControlCenterTheme.textSecondary)
      if (this.offlineCount() > 0) {
        Text('需要关注')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
          .margin({ top: ControlCenterTheme.spaceSm })
      } else {
        Text('一切正常')
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
          .margin({ top: ControlCenterTheme.spaceSm })
      }
      Text('在线设备 ' + this.onlineCount.toString() + '/' + this.totalCount.toString() +
        ' · 场景 ' + this.scenes.length.toString())
        .fontSize(12)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: ControlCenterTheme.spaceSm })
      Text('室内温度 ' + this.temp + '°C · 空气湿度 ' + this.hum + '%')
        .fontSize(12)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: ControlCenterTheme.spaceXs })
      Row() {
        Text(this.ok ? '实时连接正常' : '实时连接重连中')
          .fontSize(12)
          .fontColor(ControlCenterTheme.textPrimary)
          .layoutWeight(1)
        Button('数据监测')
          .height(ControlCenterTheme.tapTarget)
          .padding({ left: ControlCenterTheme.spaceMd, right: ControlCenterTheme.spaceMd })
          .fontSize(12)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.accent)
          .backgroundColor(ControlCenterTheme.surface)
          .borderRadius(ControlCenterTheme.radiusInner)
          .onClick(() => this.quickAction('pages/DataMonitorPage'))
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)
      .margin({ top: ControlCenterTheme.spaceMd })
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
    .padding(ControlCenterTheme.spaceLg)
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(ControlCenterTheme.accentSoft)
  }

  @Builder buildMijiaSceneStrip() {
    Column() {
      SectionTitle({ title: '快捷场景', subtitle: '一键执行常用的全屋联动', trailing: '编辑' })
      if (this.scenes.length > 0) {
        Scroll() {
          Row() {
            ForEach(this.scenes, (scene: Scene) => {
              this.buildSceneQuickCard(scene)
            }, (scene: Scene) => scene.id.toString())
          }
        }
        .scrollable(ScrollDirection.Horizontal)
        .scrollBar(BarState.Off)
        .width('100%')
      } else {
        Text('还没有可执行的场景，先去自动化创建一条吧。')
          .fontSize(12)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 12 })
      }
    }
    .width('100%')
    .margin({ top: 20 })
  }

  @Builder buildSceneQuickCard(scene: Scene) {
    Row() {
      Text(this.sceneIcon(scene.name))
        .fontSize(20)
        .width(36)
        .height(36)
        .textAlign(TextAlign.Center)
        .padding({ top: 6 })
        .borderRadius(18)
        .backgroundColor(ControlCenterTheme.accentSoft)
      Column() {
        Text(DashboardHelper.sceneName(scene.name))
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        Text(this.exe === scene.id ? '执行中...' : DashboardHelper.sceneDescription(scene.description))
          .fontSize(12)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 5 })
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start)
      .margin({ left: 10 })
    }
    .width(186)
    .padding(14)
    .borderRadius(ControlCenterTheme.radiusInner)
    .backgroundColor(ControlCenterTheme.surface)
    .border({ width: 1, color: this.exe === scene.id ? ControlCenterTheme.accent : ControlCenterTheme.border })
    .margin({ right: 10, top: 12 })
    .enabled(this.exe < 0)
    .opacity(this.exe < 0 ? 1 : 0.58)
    .onClick(() => {
      if (this.exe < 0) {
        this.requestScene(scene.id)
      }
    })
  }

  @Builder buildRoomFilter() {
    Column() {
      SectionTitle({
        title: '房间设备',
        subtitle: '按房间筛选并进入设备控制页',
        trailing: '可见 ' + this.visibleDevices().length.toString() + ' 台'
      })

      Scroll() {
        Row() {
          this.roomChip('全部', 0)
          ForEach(this.rooms, (room: Room) => {
            this.roomChip(room.name, room.id)
          }, (room: Room) => room.id.toString())
        }
      }
      .scrollable(ScrollDirection.Horizontal)
      .scrollBar(BarState.Off)
      .width('100%')
      .margin({ top: 12 })
    }
    .width('100%')
    .margin({ top: 20 })
  }

  @Builder roomChip(label: string, roomId: number) {
    Text(label)
      .fontSize(12)
      .fontWeight(this.cur === roomId ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(this.cur === roomId ? ControlCenterTheme.textOnDark : ControlCenterTheme.textSecondary)
      .padding({ left: 16, right: 16, top: 10, bottom: 10 })
      .borderRadius(ControlCenterTheme.radiusChip)
      .backgroundColor(this.cur === roomId ? ControlCenterTheme.accent : ControlCenterTheme.surface)
      .border({ width: this.cur === roomId ? 0 : 1, color: ControlCenterTheme.border })
      .margin({ right: 8 })
      .onClick(() => { this.cur = roomId })
  }

  @Builder buildDeviceGrid() {
    if (this.visibleDevices().length === 0) {
      Column() {
        Text('当前房间暂无设备')
          .fontSize(15)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        Text('可以先绑定设备，或切换到其他房间继续查看。')
          .fontSize(12)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 6 })
      }
      .width('100%')
      .padding({ top: 28, bottom: 28 })
      .alignItems(HorizontalAlign.Center)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .margin({ top: 14 })
    } else {
      GridRow({ columns: 2, gutter: 12 }) {
        ForEach(this.visibleDevices(), (device: Device) => {
          GridCol() {
            Column() {
              Row() {
                Column() {
                  Text(DashboardHelper.icon(device.type)).fontSize(22)
                }
                .width(46)
                .height(46)
                .borderRadius(18)
                .backgroundColor(ControlCenterTheme.surfaceTint)
                .justifyContent(FlexAlign.Center)
                .alignItems(HorizontalAlign.Center)

                Blank()

                Column() {
                  Row() {
                    Circle({ width: 8, height: 8 }).fill(this.dotColor(device))
                    Text(device.online ? '在线' : '离线')
                      .fontSize(12)
                      .fontColor(ControlCenterTheme.textSecondary)
                      .margin({ left: 6 })
                  }
                  .padding({ left: 10, right: 10, top: 6, bottom: 6 })
                  .borderRadius(ControlCenterTheme.radiusPill)
                  .backgroundColor(device.online ? ControlCenterTheme.accentSoft : ControlCenterTheme.surfaceTint)
                }
              }
              .width('100%')

              Text(device.name)
                .fontSize(15)
                .fontWeight(FontWeight.Bold)
                .fontColor(ControlCenterTheme.textPrimary)
                .margin({ top: 16 })
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })

              Text(this.roomName(device.room_id))
                .fontSize(12)
                .fontColor(ControlCenterTheme.textTertiary)
                .margin({ top: 4 })
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })

              Text(DashboardHelper.status(device))
                .fontSize(12)
                .fontColor(ControlCenterTheme.textSecondary)
                .margin({ top: 8 })
                .maxLines(2)
                .textOverflow({ overflow: TextOverflow.Ellipsis })

              Text('进入控制')
                .fontSize(12)
                .fontColor(ControlCenterTheme.accent)
                .fontWeight(FontWeight.Bold)
                .margin({ top: 18 })
            }
            .padding(16)
            .borderRadius(ControlCenterTheme.radiusCard)
            .backgroundColor(ControlCenterTheme.surface)
            .border({ width: 1, color: ControlCenterTheme.border })
            .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
            .onClick(() => {
              this.getUIContext().getRouter().pushUrl({
                url: 'pages/DeviceRemotePage',
                params: { 'deviceType': device.type, 'deviceId': device.id }
              })
            })
          }
        }, (device: Device) => device.id.toString())
      }
      .margin({ top: 14 })
    }
  }

  @Builder buildActivityPanel() {
    Column() {
      SectionTitle({
        title: '最近活动',
        subtitle: '保留关键操作和状态变化的可见性',
        trailing: this.recentLogs.length > 0 ? '最新 ' + Math.min(this.recentLogs.length, 5).toString() + ' 条' : ''
      })

      Column() {
        if (this.recentLogs.length === 0) {
          Column() {
            Text('最近还没有新的操作记录')
              .fontSize(14)
              .fontWeight(FontWeight.Medium)
              .fontColor(ControlCenterTheme.textPrimary)
            Text('设备指令、自动化和场景执行都会显示在这里。')
              .fontSize(12)
              .fontColor(ControlCenterTheme.textSecondary)
              .margin({ top: 4 })
          }
          .width('100%')
          .padding({ top: 20, bottom: 20 })
          .alignItems(HorizontalAlign.Center)
        } else {
          ForEach(this.recentLogs.slice(0, 3), (item: LogItem) => {
            Row() {
              Column() {
                Text(DashboardHelper.logLabel(item))
                  .fontSize(14)
                  .fontWeight(FontWeight.Bold)
                  .fontColor(ControlCenterTheme.textPrimary)
                Text(this.formatLogDetail(item))
                  .fontSize(12)
                  .fontColor(ControlCenterTheme.textSecondary)
                  .margin({ top: 4 })
                  .maxLines(2)
                  .textOverflow({ overflow: TextOverflow.Ellipsis })
              }
              .layoutWeight(1)
              .alignItems(HorizontalAlign.Start)

              Text(this.shortTime(item.timestamp))
                .fontSize(11)
                .fontColor(ControlCenterTheme.textTertiary)
                .margin({ left: 10 })
            }
            .width('100%')
            .padding({ top: 12, bottom: 12 })
            .border({ width: { bottom: 0.5 }, color: ControlCenterTheme.border })
          }, (item: LogItem) => item.id.toString())
        }
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 8, bottom: 8 })
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .border({ width: 1, color: ControlCenterTheme.border })
      .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
      .margin({ top: 12 })
    }
    .width('100%')
    .margin({ top: 20 })
  }

}
