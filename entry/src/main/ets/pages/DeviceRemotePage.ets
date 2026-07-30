import { callService, buildEntityId, getAesKey, getDevicesForUi } from '../common/ApiClient'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { SectionTitle, StatusBanner, MetricChip } from '../common/ControlCenterKit'
import { generateAuthCode } from '../common/CryptoUtil'
import { UiText } from '../common/UiText'
import { Device, parseDeviceStatus, CommandParams } from '../model/DeviceModel'

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

function localizeSuccessMessage(message: string, fallback: string): string {
  if (!message) {
    return fallback
  }
  if (/[\u4e00-\u9fff]/.test(message)) {
    return message
  }
  if (message.indexOf('command dispatched') >= 0) {
    return '设备指令已下发'
  }
  return fallback
}

@Entry
@Component
struct DeviceRemotePage {
  @State dt: string = ''
  @State ds: Device[] = []
  @State roomDevices: Device[] = []
  @State ix: number = 0
  @State loading: boolean = false
  @State commandBusy: boolean = false
  @State errorMessage: string = ''
  @State successMessage: string = ''

  @State ltOn: boolean = false
  @State ltBr: number = 80
  @State ltCl: string = 'warm'

  @State acOn: boolean = false
  @State acTp: number = 26
  @State acMd: string = 'cool'
  @State acFn: string = 'auto'
  @State acBr: string = ''

  @State dlLk: boolean = true
  @State dlCd: number = 0
  @State dlMsg: string = ''
  @State dlSh: boolean = false

  private dlT: number = -1
  private dlMT: number = -1
  private sliderTimer: number = -1
  private environmentTimer: number = -1

  @State ctPs: number = 0

  @State huOn: boolean = false
  @State huLv: number = 2
  @State huTg: number = 60

  private pendingDeviceId: number = 0

  aboutToAppear(): void {
    let params = this.getUIContext().getRouter().getParams() as Record<string, Object>
    if (params !== null && params !== undefined && params['deviceType'] !== undefined) {
      this.dt = params['deviceType'] as string
    }
    if (params !== null && params !== undefined && params['deviceId'] !== undefined) {
      this.pendingDeviceId = params['deviceId'] as number
    }
    this.load()
    this.startEnvironmentRefresh()
  }

  aboutToDisappear(): void {
    this.clr()
    if (this.sliderTimer > 0) {
      clearTimeout(this.sliderTimer)
      this.sliderTimer = -1
    }
    if (this.environmentTimer > 0) {
      clearInterval(this.environmentTimer)
      this.environmentTimer = -1
    }
    if (this.dlMT > 0) {
      clearTimeout(this.dlMT)
      this.dlMT = -1
    }
  }

  clr(): void {
    if (this.dlT > 0) {
      clearTimeout(this.dlT)
      this.dlT = -1
    }
    this.dlCd = 0
  }

  cur(): Device | null {
    if (this.ix < 0 || this.ix >= this.ds.length) {
      return null
    }
    return this.ds[this.ix]
  }

  currentOnline(): boolean {
    let current = this.cur()
    return current !== null && current.online
  }

  async refreshRoomEnvironment(): Promise<void> {
    let current = this.cur()
    if (!current) {
      return
    }
    try {
      this.roomDevices = await getDevicesForUi(current.room_id)
    } catch (_) {
      // Keep the last valid room readings when the periodic refresh fails.
    }
  }

  startEnvironmentRefresh(): void {
    if (this.environmentTimer > 0) {
      clearInterval(this.environmentTimer)
    }
    this.environmentTimer = setInterval(() => {
      this.refreshRoomEnvironment()
    }, 5000)
  }

  roomSensorValue(type: string, suffix: string, unavailable: string): string {
    for (let i = 0; i < this.roomDevices.length; i++) {
      let sensor = this.roomDevices[i]
      if (sensor.type !== type) {
        continue
      }
      let status = parseDeviceStatus(sensor.status_json)
      if (status.value > 0) {
        return status.value.toString() + suffix
      }
    }
    return unavailable
  }

  roomTemperature(): string {
    return this.roomSensorValue('temperature_sensor', '°C', '温度未采集')
  }

  roomHumidity(): string {
    return this.roomSensorValue('humidity_sensor', '%', '湿度未采集')
  }

  async load(): Promise<void> {
    this.loading = true
    try {
      let targetId = 0
      let current = this.cur()
      if (current) {
        targetId = current.id
      }
      if (this.pendingDeviceId > 0) {
        targetId = this.pendingDeviceId
      }
      this.ds = await getDevicesForUi(undefined, this.dt)
      if (this.ds.length === 0) {
        this.ix = 0
        this.clr()
        return
      }
      let next = 0
      if (targetId > 0) {
        for (let i = 0; i < this.ds.length; i++) {
          if (this.ds[i].id === targetId) {
            next = i
            break
          }
        }
      }
      this.pendingDeviceId = 0
      this.sl(next)
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '加载设备控制页失败')
    } finally {
      this.loading = false
    }
  }

  sl(i: number): void {
    if (i < 0 || i >= this.ds.length) {
      return
    }
    if (this.sliderTimer > 0) {
      clearTimeout(this.sliderTimer)
      this.sliderTimer = -1
    }
    this.ix = i
    let device = this.ds[i]
    let status = parseDeviceStatus(device.status_json)
    this.successMessage = ''
    if (this.dt === 'light') {
      this.ltOn = status.power === 'on'
      this.ltBr = status.brightness || 80
      this.ltCl = status.color || 'warm'
    } else if (this.dt === 'ac') {
      this.acOn = status.power === 'on'
      this.acTp = status.temp || 26
      this.acMd = status.mode || 'cool'
      this.acFn = status.fan || 'auto'
      this.acBr = status.brand || (device.brand || '')
    } else if (this.dt === 'door_lock') {
      this.dlLk = status.locked
    } else if (this.dt === 'curtain') {
      this.ctPs = status.position || 0
    } else if (this.dt === 'humidifier') {
      this.huOn = status.power === 'on'
      this.huLv = status.level || 2
      this.huTg = status.target_humidity || 60
    }
    this.refreshRoomEnvironment()
  }

  async cmd(id: number, action: string, params?: Object): Promise<void> {
    this.commandBusy = true
    this.errorMessage = ''
    this.successMessage = ''
    try {
      let entityId = buildEntityId(this.dt, id)
      let result = await callService(entityId, action, params)
      this.successMessage = localizeSuccessMessage(result.message, '设备控制成功')
      if (result.changed_states.length > 0) {
        let updated = result.changed_states[0]
        let current = this.cur()
        if (current) {
          current.status_json = JSON.stringify(updated.attributes)
          current.updated_at = updated.last_updated
          current.last_seen_at = updated.last_updated
          let onlineVal = updated.attributes['online']
          if (onlineVal !== undefined && onlineVal !== null) {
            current.online = onlineVal as boolean
          }
          let summaryVal = updated.attributes['status_summary']
          if (summaryVal !== undefined && summaryVal !== null) {
            current.status_summary = summaryVal as string
          }
          this.sl(this.ix)
        }
      }
      await this.load()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '设备操作失败')
    } finally {
      this.commandBusy = false
    }
  }

  async cmdCurrent(action: string, params?: Object): Promise<void> {
    let current = this.cur()
    if (!current || this.commandBusy) {
      return
    }
    await this.cmd(current.id, action, params)
  }

  queueSliderCommand(deviceId: number, action: string, params: CommandParams): void {
    if (this.sliderTimer > 0) {
      clearTimeout(this.sliderTimer)
    }
    this.sliderTimer = setTimeout(() => {
      this.sliderTimer = -1
      this.cmd(deviceId, action, params)
    }, 250)
  }

  tn(): string {
    switch (this.dt) {
      case 'light': return '灯光控制'
      case 'ac': return '空调控制'
      case 'door_lock': return '门锁控制'
      case 'curtain': return '窗帘控制'
      case 'humidifier': return '加湿器控制'
      default: return '设备控制'
    }
  }

  stateLabel(): string {
    if (this.dt === 'light') return this.ltOn ? '灯光已开启' : '灯光已关闭'
    if (this.dt === 'ac') return this.acOn ? '空调运行中' : '空调待机中'
    if (this.dt === 'door_lock') return this.dlLk ? '门锁已上锁' : '门锁已解锁'
    if (this.dt === 'curtain') return '开合位置 ' + this.ctPs + '%'
    if (this.dt === 'humidifier') return this.huOn ? '正在加湿' : '加湿器已关闭'
    return '设备就绪'
  }

  currentStatusLabel(): string {
    return this.stateLabel() + ' · ' + this.roomTemperature() + ' · ' + this.roomHumidity()
  }

  primaryMetric(): string {
    if (this.dt === 'light') return this.ltBr + '%'
    if (this.dt === 'ac') return this.acTp + '°C'
    if (this.dt === 'door_lock') return this.dlLk ? '上锁' : '解锁'
    if (this.dt === 'curtain') return this.ctPs + '%'
    if (this.dt === 'humidifier') return this.huTg + '%'
    return '--'
  }

  metricCaption(): string {
    if (this.dt === 'light') return '当前亮度'
    if (this.dt === 'ac') return '目标温度'
    if (this.dt === 'door_lock') return '门锁状态'
    if (this.dt === 'curtain') return '开合位置'
    if (this.dt === 'humidifier') return '目标湿度'
    return '当前状态'
  }

  secondaryMetricLabel(): string {
    if (this.dt === 'light') return this.lightColorLabel()
    if (this.dt === 'ac') return this.acMd + ' / ' + this.acFn
    if (this.dt === 'door_lock') return this.dlCd > 0 ? this.dlCd.toString() + ' 秒后回锁' : '安全守护中'
    if (this.dt === 'curtain') return this.currentOnline() ? '可精细调节' : '等待恢复在线'
    if (this.dt === 'humidifier') return '档位 ' + this.huLv.toString()
    return '智能家居'
  }

  lightColorLabel(): string {
    if (this.ltCl === 'warm') return '暖光'
    if (this.ltCl === 'natural') return '自然光'
    if (this.ltCl === 'cool') return '冷光'
    if (/[\u4e00-\u9fff]/.test(this.ltCl)) return this.ltCl
    if (!this.ltCl) return '未知模式'
    return '其他模式'
  }

  heroIcon(): string {
    if (this.dt === 'light') return '\uD83D\uDCA1'
    if (this.dt === 'ac') return '\u2744\uFE0F'
    if (this.dt === 'door_lock') return this.dlLk ? '\uD83D\uDD12' : '\uD83D\uDD13'
    if (this.dt === 'curtain') return '\uD83E\uDE9B'
    if (this.dt === 'humidifier') return '\uD83D\uDCA8'
    return '\uD83D\uDD0C'
  }

  heroTone(): string {
    if (!this.currentOnline()) {
      return 'warning'
    }
    if (this.dt === 'door_lock' && !this.dlLk) {
      return 'warning'
    }
    return 'success'
  }

  autoLockTick(): void {
    this.clr()
    this.dlCd = 5
    let tick = () => {
      this.dlCd--
      if (this.dlCd <= 0) {
        this.dlCd = 0
        this.doDl()
        return
      }
      if (this.dlLk) {
        this.clr()
        return
      }
      this.dlT = setTimeout(tick, 1000)
    }
    this.dlT = setTimeout(tick, 1000)
  }

  async doDl(): Promise<void> {
    try {
      let current = this.cur()
      if (!current) {
        return
      }
      let id = current.id
      if (this.dlLk) {
        let code = await generateAuthCode(getAesKey())
        let params = new CommandParams()
        params.auth_code = code
        await this.cmd(id, 'unlock', params)
        this.dlMsg = '门锁解锁成功'
        this.dlSh = true
        this.autoLockTick()
      } else {
        this.clr()
        await this.cmd(id, 'lock')
        this.dlMsg = '门锁已重新上锁'
        this.dlSh = true
      }
      this.dlMT = setTimeout(() => {
        this.dlSh = false
        this.dlMT = -1
      }, 2500)
    } catch (err) {
      this.dlMsg = '门锁操作失败'
      this.dlSh = true
    }
  }

  build() {
    Column() {
      if (this.loading) {
        this.buildLoading()
      } else if (this.ds.length === 0) {
        this.buildEmpty()
      } else {
        Scroll() {
          Column() {
            this.buildTopBar()
            this.buildFeedback()
            this.buildControlHero()
            this.buildDeviceSwitcher()
            if (this.dt === 'light') {
              this.buildLightPanel()
            } else if (this.dt === 'ac') {
              this.buildAcPanel()
            } else if (this.dt === 'door_lock') {
              this.buildLockPanel()
            } else if (this.dt === 'curtain') {
              this.buildCurtainPanel()
            } else if (this.dt === 'humidifier') {
              this.buildHumidifierPanel()
            }
          }
          .padding({ left: 16, right: 16, top: 16, bottom: 28 })
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(ControlCenterTheme.pageBg)
  }

  @Builder buildTopBar() {
    Row() {
      Row() {
        SymbolGlyph($r('sys.symbol.chevron_left'))
          .fontSize(20)
          .fontColor([ControlCenterTheme.textPrimary])
      }
      .width(ControlCenterTheme.tapTarget)
      .height(ControlCenterTheme.tapTarget)
      .borderRadius(ControlCenterTheme.radiusInner)
      .backgroundColor(ControlCenterTheme.surface)
      .justifyContent(FlexAlign.Center)
      .alignItems(VerticalAlign.Center)
      .shadow({ radius: 12, color: ControlCenterTheme.shadowSoft, offsetY: 4 })
      .accessibilityText('返回')
      .onClick(() => this.getUIContext().getRouter().back())

      Text(this.tn())
        .fontSize(ControlCenterTheme.sectionTitleSize)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ left: 10 })
      Blank()
      Button() {
        SymbolGlyph($r('sys.symbol.repeat_1'))
          .fontSize(20)
          .fontColor([ControlCenterTheme.accent])
      }
        .width(ControlCenterTheme.tapTarget)
        .height(ControlCenterTheme.tapTarget)
        .borderRadius(ControlCenterTheme.radiusInner)
        .backgroundColor(ControlCenterTheme.accentSoft)
        .accessibilityText('刷新设备状态')
        .onClick(() => this.load())
    }
    .width('100%')
  }

  @Builder buildFeedback() {
    if (this.successMessage) {
      StatusBanner({
        message: this.successMessage,
        detail: '状态已刷新',
        tone: 'success'
      }).margin({ top: 14 })
    }

    if (this.errorMessage) {
      StatusBanner({
        message: this.errorMessage,
        detail: '请重试或检查设备在线状态',
        tone: 'danger'
      }).margin({ top: this.successMessage ? 8 : 14 })
    }
  }

  @Builder buildControlHero() {
    Column() {
      Text(this.heroIcon())
        .fontSize(50)
        .width(94)
        .height(94)
        .textAlign(TextAlign.Center)
        .padding({ top: 20 })
        .borderRadius(47)
        .backgroundColor(ControlCenterTheme.accentSoft)
      Text(this.cur() ? (this.cur() as Device).name : '未选择设备')
        .fontSize(23)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ top: 14 })
      Text(this.currentStatusLabel())
        .fontSize(13)
        .fontColor(ControlCenterTheme.accent)
        .margin({ top: 6 })
      Row() {
        MetricChip({ label: this.metricCaption(), value: this.primaryMetric(), tone: 'accent' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({ label: '房间', value: this.cur() && (this.cur() as Device).room_name ? (this.cur() as Device).room_name : '未分配', tone: 'neutral' }).layoutWeight(1)
      }
      .width('100%')
      .margin({ top: 20 })
      Text('常用操作')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
        .width('100%')
        .margin({ top: 20 })
      Text(this.currentOnline() ? '设备在线，可立即执行控制指令' : '设备离线，指令将尝试下发')
        .fontSize(12)
        .fontColor(ControlCenterTheme.textSecondary)
        .width('100%')
        .margin({ top: 5 })
    }
    .width('100%')
    .padding(22)
    .borderRadius(ControlCenterTheme.radiusHero)
    .backgroundColor(ControlCenterTheme.surface)
    .border({ width: 1, color: ControlCenterTheme.border })
    .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
    .alignItems(HorizontalAlign.Center)
  }

  @Builder buildStatusHero() {
    Column() {
      Row() {
        Column() {
          Text(this.heroIcon())
            .fontSize(28)
        }
        .width(52)
        .height(52)
        .borderRadius(18)
        .backgroundColor(ControlCenterTheme.accentSoft)
        .justifyContent(FlexAlign.Center)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text(this.cur() ? (this.cur() as Device).name : '未选择设备')
            .fontSize(21)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text(this.currentStatusLabel())
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 5 })
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1)
        .margin({ left: 12 })

        Text(this.currentOnline() ? '在线' : '离线')
          .fontSize(ControlCenterTheme.assistSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(this.currentOnline() ? ControlCenterTheme.accent : '#A56A13')
          .padding({ left: 10, right: 10, top: 6, bottom: 6 })
          .borderRadius(ControlCenterTheme.radiusPill)
          .backgroundColor(this.currentOnline() ? ControlCenterTheme.accentSoft : ControlCenterTheme.warningSoft)
      }
      .width('100%')

      Row() {
        MetricChip({ label: this.metricCaption(), value: this.primaryMetric(), tone: 'accent' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({
          label: this.cur() && (this.cur() as Device).room_name ? (this.cur() as Device).room_name : '房间信息',
          value: this.cur() && (this.cur() as Device).brand ? (this.cur() as Device).brand : this.secondaryMetricLabel(),
          tone: this.heroTone(),
          inverse: false
        }).layoutWeight(1)
      }
      .width('100%')
      .margin({ top: 18 })

      Row() {
        MetricChip({ label: '室内温度', value: this.roomTemperature(), tone: 'accent' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({ label: '室内湿度', value: this.roomHumidity(), tone: 'warning' }).layoutWeight(1)
      }
      .width('100%')
      .margin({ top: 10 })

      StatusBanner({
        message: this.currentOnline() ? '当前设备可立即控制' : '设备离线，仍可尝试控制',
        detail: this.currentOnline() ? '关键操作已解锁' : '指令将通过 MQTT 下发',
        tone: this.currentOnline() ? 'success' : 'warning'
      }).margin({ top: 18 })
    }
    .width('100%')
    .padding(20)
    .borderRadius(ControlCenterTheme.radiusHero)
    .backgroundColor(ControlCenterTheme.surface)
    .border({ width: 1, color: ControlCenterTheme.border })
    .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
    .margin({ top: 16 })
  }

  @Builder buildDeviceSwitcher() {
    if (this.ds.length > 1) {
      Scroll() {
        Row() {
          ForEach(this.ds, (device: Device, i: number) => {
            Text(device.name)
              .fontSize(12)
              .fontWeight(this.ix === i ? FontWeight.Bold : FontWeight.Medium)
              .fontColor(this.ix === i ? ControlCenterTheme.textOnDark : ControlCenterTheme.textSecondary)
              .padding({ left: 16, right: 16, top: 10, bottom: 10 })
              .height(ControlCenterTheme.tapTarget)
              .borderRadius(ControlCenterTheme.radiusChip)
              .backgroundColor(this.ix === i ? ControlCenterTheme.accent : ControlCenterTheme.surface)
              .border({ width: 1, color: this.ix === i ? ControlCenterTheme.accent : ControlCenterTheme.border })
              .margin({ right: 8 })
              .onClick(() => this.sl(i))
          }, (device: Device) => device.id.toString())
        }
      }
      .scrollable(ScrollDirection.Horizontal)
      .scrollBar(BarState.Off)
      .width('100%')
      .margin({ top: 16 })
    }
  }

  @Builder buildPanelHeader(title: string, subtitle: string, trailing: string = '') {
    SectionTitle({ title: title, subtitle: subtitle, trailing: trailing })
  }

  @Builder buildPrimaryButton(label: string, color: string, action: () => void) {
    Button(this.commandBusy ? '执行中...' : label)
      .type(ButtonType.Capsule)
      .width('100%')
      .height(52)
      .fontSize(16)
      .fontWeight(FontWeight.Bold)
      .backgroundColor(color)
      .fontColor('#FFFFFF')
      .borderRadius(18)
      .enabled(!this.commandBusy)
      .margin({ top: 14 })
      .onClick(action)
  }

  @Builder buildGhostButton(label: string, bg: string, fg: string, action: () => void) {
    Button(label)
      .type(ButtonType.Capsule)
      .layoutWeight(1)
      .height(48)
      .fontSize(14)
      .fontWeight(FontWeight.Bold)
      .backgroundColor(bg)
      .fontColor(fg)
      .borderRadius(16)
      .enabled(!this.commandBusy)
      .onClick(action)
  }

  @Builder buildLightPanel() {
    Column() {
      this.buildPanelHeader('关键操作', '开关与亮度控制', this.ltOn ? '灯光开启中' : '灯光已关闭')

      Row() {
        MetricChip({ label: '供电状态', value: this.ltOn ? '开启' : '关闭', tone: this.ltOn ? 'success' : 'neutral' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({ label: '色温模式', value: this.lightColorLabel(), tone: 'warning' }).layoutWeight(1)
      }
      .width('100%')
      .margin({ top: 12 })

      this.buildPrimaryButton(this.ltOn ? '关闭灯光' : '开启灯光', this.ltOn ? ControlCenterTheme.danger : ControlCenterTheme.accent, () => {
        if (this.ltOn) {
          this.cmdCurrent('off')
        } else {
          let params = new CommandParams()
          params.brightness = this.ltBr
          params.color = this.ltCl
          this.cmdCurrent('on', params)
        }
      })

      Column() {
        this.buildPanelHeader('亮度微调', '拖动滑块调整当前灯光', this.ltBr + '%')
        Row() {
          Text('0%').fontSize(ControlCenterTheme.assistSize).fontColor(ControlCenterTheme.textSecondary)
          Blank()
          Text('100%').fontSize(ControlCenterTheme.assistSize).fontColor(ControlCenterTheme.textSecondary)
        }
        .width('100%')
        .margin({ top: 12, bottom: 8 })
        Slider({ value: this.ltBr, min: 0, max: 100, step: 5, style: SliderStyle.OutSet })
          .width('100%')
          .blockColor(ControlCenterTheme.accent)
          .trackColor('#D9E2EA')
          .selectedColor(ControlCenterTheme.accent)
          .onChange((v: number) => {
            this.ltBr = Math.round(v)
            let current = this.cur()
            if (current && this.ltOn && !this.commandBusy) {
              let params = new CommandParams()
              params.brightness = this.ltBr
              this.queueSliderCommand(current.id, 'set', params)
            }
          })
      }
      .width('100%')
      .padding(16)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .border({ width: 1, color: ControlCenterTheme.border })
      .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
      .margin({ top: 14 })
    }
    .width('100%')
    .margin({ top: 18 })
  }

  @Builder buildAcPanel() {
    Column() {
      this.buildPanelHeader('温度控制', '突出当前温度设定与主开关', this.acMd)

      Column() {
        Row() {
          Text('\u2212')
            .fontSize(30)
            .fontColor(ControlCenterTheme.textSecondary)
            .onClick(() => {
              this.acTp = Math.max(16, this.acTp - 1)
              if (this.acOn && !this.commandBusy) {
                let params = new CommandParams()
                params.temp = this.acTp
                this.cmdCurrent('set', params)
              }
            })
          Blank()
          Column() {
            Text(this.acTp + '°C')
              .fontSize(48)
              .fontWeight(FontWeight.Bold)
              .fontColor(ControlCenterTheme.textPrimary)
            Text(this.acBr || '空调设备')
              .fontSize(12)
              .fontColor(ControlCenterTheme.textSecondary)
              .margin({ top: 4 })
          }
          .alignItems(HorizontalAlign.Center)
          Blank()
          Text('+')
            .fontSize(30)
            .fontColor(ControlCenterTheme.textSecondary)
            .onClick(() => {
              this.acTp = Math.min(30, this.acTp + 1)
              if (this.acOn && !this.commandBusy) {
                let params = new CommandParams()
                params.temp = this.acTp
                this.cmdCurrent('set', params)
              }
            })
        }
        .width('100%')
        .padding({ top: 18, bottom: 18 })

        Row() {
          MetricChip({ label: '运行模式', value: this.acMd, tone: 'accent' }).layoutWeight(1)
          Blank().width(10)
          MetricChip({ label: '风速', value: this.acFn, tone: 'warning' }).layoutWeight(1)
        }
        .width('100%')
      }
      .padding(16)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .border({ width: 1, color: ControlCenterTheme.border })
      .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
      .margin({ top: 12 })

      this.buildPrimaryButton(this.acOn ? '关闭空调' : '开启空调', this.acOn ? ControlCenterTheme.danger : ControlCenterTheme.accent, () => {
        if (this.acOn) {
          this.cmdCurrent('off')
        } else {
          let p = new CommandParams()
          p.mode = this.acMd
          p.temp = this.acTp
          p.fan = this.acFn
          this.cmdCurrent('on', p)
        }
      })
    }
    .width('100%')
    .margin({ top: 18 })
  }

  @Builder buildLockPanel() {
    Column() {
      this.buildPanelHeader('门锁状态', '把当前安全状态和关键动作放在最前面', this.dlLk ? '安全中' : '已解锁')

      Column() {
        Text(this.dlLk ? '\uD83D\uDD12' : '\uD83D\uDD13').fontSize(76)
        Text(this.dlLk ? '门锁当前处于上锁状态' : '门锁当前处于解锁状态')
          .fontSize(14)
          .fontColor(this.dlLk ? ControlCenterTheme.accent : ControlCenterTheme.warning)
          .margin({ top: 14 })
      }
      .width('100%')
      .padding({ top: 26, bottom: 26 })
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .border({ width: 1, color: ControlCenterTheme.border })
      .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
      .alignItems(HorizontalAlign.Center)
      .margin({ top: 12 })

      this.buildPrimaryButton(this.dlLk ? '解锁门锁' : '重新上锁', this.dlLk ? ControlCenterTheme.warning : ControlCenterTheme.accent, () => this.doDl())

      if (this.dlSh) {
        StatusBanner({
          message: this.dlMsg,
          detail: this.dlCd > 0 ? this.dlCd.toString() + ' 秒后自动回锁' : '',
          tone: this.dlLk ? 'success' : 'warning'
        }).margin({ top: 10 })
      }
    }
    .width('100%')
    .margin({ top: 18 })
  }

  @Builder buildCurtainPanel() {
    Column() {
      this.buildPanelHeader('窗帘控制', '开合状态 + 快捷操作 + 精细滑动控制', this.ctPs + '%')

      Column() {
        Text('\uD83E\uDE9B').fontSize(60)
        Text(this.ctPs + '%')
          .fontSize(42)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
          .margin({ top: 10 })
        Text('当前开合位置')
          .fontSize(12)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 4 })
      }
      .width('100%')
      .padding({ top: 24, bottom: 24 })
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .border({ width: 1, color: ControlCenterTheme.border })
      .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
      .alignItems(HorizontalAlign.Center)
      .margin({ top: 12 })

      Row() {
        this.buildGhostButton('打开', ControlCenterTheme.successSoft, '#1B8267', () => this.cmdCurrent('open'))
        Blank().width(10)
        this.buildGhostButton('关闭', ControlCenterTheme.warningSoft, '#9A651D', () => this.cmdCurrent('close'))
      }
      .width('100%')
      .margin({ top: 14 })

      Column() {
        this.buildPanelHeader('位置微调', '滑动调整到目标开合度', this.ctPs + '%')
        Row() {
          Text('关闭').fontSize(ControlCenterTheme.assistSize).fontColor(ControlCenterTheme.textSecondary)
          Blank()
          Text('打开').fontSize(ControlCenterTheme.assistSize).fontColor(ControlCenterTheme.textSecondary)
        }
        .width('100%')
        .margin({ top: 12, bottom: 8 })
        Slider({ value: this.ctPs, min: 0, max: 100, step: 5, style: SliderStyle.OutSet })
          .width('100%')
          .blockColor(ControlCenterTheme.accent)
          .trackColor('#D9E2EA')
          .selectedColor(ControlCenterTheme.accent)
          .onChange((v: number) => {
            this.ctPs = Math.round(v)
            let current = this.cur()
            if (current && !this.commandBusy) {
              let params = new CommandParams()
              params.position = this.ctPs
              this.queueSliderCommand(current.id, 'set', params)
            }
          })
      }
      .width('100%')
      .padding(16)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .border({ width: 1, color: ControlCenterTheme.border })
      .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
      .margin({ top: 14 })
    }
    .width('100%')
    .margin({ top: 18 })
  }

  @Builder buildHumidifierPanel() {
    Column() {
      this.buildPanelHeader('湿度控制', '把目标湿度和开关操作放在同一个决策区', this.huTg + '%')

      Row() {
        MetricChip({ label: '供电状态', value: this.huOn ? '开启' : '关闭', tone: this.huOn ? 'success' : 'neutral' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({ label: '工作档位', value: this.huLv.toString(), tone: 'warning' }).layoutWeight(1)
      }
      .width('100%')
      .margin({ top: 12 })

      this.buildPrimaryButton(this.huOn ? '关闭加湿器' : '开启加湿器', this.huOn ? ControlCenterTheme.danger : ControlCenterTheme.accent, () => {
        if (this.huOn) {
          this.cmdCurrent('off')
        } else {
          let p = new CommandParams()
          p.level = this.huLv
          p.target_humidity = this.huTg
          this.cmdCurrent('on', p)
        }
      })

      Column() {
        this.buildPanelHeader('目标湿度', '拖动滑块调整运行目标', this.huTg + '%')
        Row() {
          Text('35%').fontSize(ControlCenterTheme.assistSize).fontColor(ControlCenterTheme.textSecondary)
          Blank()
          Text('80%').fontSize(ControlCenterTheme.assistSize).fontColor(ControlCenterTheme.textSecondary)
        }
        .width('100%')
        .margin({ top: 12, bottom: 8 })
        Slider({ value: this.huTg, min: 35, max: 80, step: 5, style: SliderStyle.OutSet })
          .width('100%')
          .blockColor(ControlCenterTheme.accent)
          .trackColor('#D9E2EA')
          .selectedColor(ControlCenterTheme.accent)
          .onChange((v: number) => {
            this.huTg = Math.round(v)
            let current = this.cur()
            if (current && this.huOn && !this.commandBusy) {
              let p = new CommandParams()
              p.target_humidity = this.huTg
              this.queueSliderCommand(current.id, 'set', p)
            }
          })
      }
      .width('100%')
      .padding(16)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
      .border({ width: 1, color: ControlCenterTheme.border })
      .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
      .margin({ top: 14 })
    }
    .width('100%')
    .margin({ top: 18 })
  }

  @Builder buildLoading() {
    Column() {
      LoadingProgress().width(34).height(34).color(ControlCenterTheme.accent)
      Text('正在加载设备控制面板...')
        .fontSize(13)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: 14 })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }

  @Builder buildEmpty() {
    Column() {
      Text('当前类型暂无已绑定设备')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
      Text('请先到设备管理中绑定设备，再返回这里控制。')
        .fontSize(12)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: 8 })
      Button('返回')
        .type(ButtonType.Capsule)
        .width(160)
        .height(44)
        .fontSize(14)
        .backgroundColor(ControlCenterTheme.accent)
        .fontColor('#FFFFFF')
        .borderRadius(14)
        .margin({ top: 20 })
        .onClick(() => this.getUIContext().getRouter().back())
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(ControlCenterTheme.pageBg)
  }
}
