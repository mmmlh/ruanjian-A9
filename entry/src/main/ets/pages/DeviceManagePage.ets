import { getDevicesForUi, getRooms, updateDeviceName, deleteDevice, discoverDevices, bindDevice } from '../common/ApiClient'
import { Room, Device, DiscoveredDevice } from '../model/DeviceModel'
import { UiText } from '../common/UiText'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { AppBottomNav, StatusBanner } from '../common/ControlCenterKit'

const DEVICE_ACTION_PRIMARY: string = ControlCenterTheme.accent
const DEVICE_ACTION_SECONDARY_BG: string = ControlCenterTheme.surfaceMuted
const DEVICE_ACTION_SECONDARY_FG: string = ControlCenterTheme.textPrimary

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

class DevType {
  label: string = ''
  value: string = ''
}

let DEV_TYPES: DevType[] = [
  { label: '灯光', value: 'light' },
  { label: '空调', value: 'ac' },
  { label: '门锁', value: 'door_lock' },
  { label: '温度传感器', value: 'temperature_sensor' },
  { label: '湿度传感器', value: 'humidity_sensor' },
  { label: '人体传感器', value: 'pir_sensor' },
  { label: '窗帘', value: 'curtain' },
  { label: '加湿器', value: 'humidifier' }
]

class DeviceHelper {
  static icon(type: string): string {
    switch (type) {
      case 'light': return '\uD83D\uDCA1'
      case 'ac': return '\u2744\uFE0F'
      case 'door_lock': return '\uD83D\uDD12'
      case 'temperature_sensor': return '\uD83C\uDF21\uFE0F'
      case 'humidity_sensor': return '\uD83D\uDCA7'
      case 'pir_sensor': return '\uD83D\uDC63'
      case 'curtain': return '\uD83E\uDE9B'
      case 'humidifier': return '\u2728'
      default: return '\uD83D\uDD0C'
    }
  }

  static typeLabel(type: string): string {
    for (let i = 0; i < DEV_TYPES.length; i++) {
      if (DEV_TYPES[i].value === type) {
        return DEV_TYPES[i].label
      }
    }
    return type
  }

  static roomLabel(candidate: DiscoveredDevice): string {
    if (candidate.room_hint) {
      return candidate.room_hint
    }
    if (candidate.room) {
      return candidate.room
    }
    return '未分配房间'
  }

  static summaryText(summary: string, fallback: string): string {
    if (!summary) {
      return fallback
    }
    if (/[\u4e00-\u9fff]/.test(summary)) {
      return summary
    }
    if (summary === 'Power off') return '已关闭'
    if (summary === 'Power on') return '已开启'
    if (summary === 'Standby') return '待机中'
    if (summary === 'Locked') return '已上锁'
    if (summary === 'Unlocked') return '已解锁'
    if (summary === 'Securely locked') return '已安全上锁'
    if (summary === 'Fully closed') return '已完全关闭'
    if (summary === 'Motion detected') return '检测到活动'
    if (summary === 'No motion') return '区域空闲'
    if (summary === 'Area idle') return '区域空闲'
    if (summary === 'Unknown position') return '位置未知'
    if (summary.indexOf('Brightness ') === 0) return '亮度 ' + summary.substring('Brightness '.length)
    if (summary.indexOf('Cooling ') === 0) return '制冷 ' + summary.substring('Cooling '.length)
    if (summary.indexOf('Open ') === 0) return '开启 ' + summary.substring('Open '.length)
    if (summary.indexOf('Target humidity ') === 0) return '目标湿度 ' + summary.substring('Target humidity '.length)
    return fallback
  }

  static seenText(value: string, fallback: string): string {
    if (!value) {
      return fallback
    }
    if (value.length >= 16) {
      return '最近上报 ' + value.substring(5, 16)
    }
    return '最近上报 ' + value
  }
}

@Entry
@Component
struct DeviceManagePage {
  @State devices: Device[] = []
  @State rooms: Room[] = []
  @State discovered: DiscoveredDevice[] = []
  @State loading: boolean = false
  @State scanning: boolean = false
  @State binding: boolean = false
  @State saving: boolean = false
  @State deletingId: number = -1
  @State showEdit: boolean = false
  @State eid: number = -1
  @State en: string = ''
  @State eb: string = ''
  @State bindRoomId: number = 0
  @State bindName: string = ''
  @State bindTargetId: string = ''
  @State err: string = ''
  @State ok: string = ''
  @State viewMode: number = 0
  @State initialLoadComplete: boolean = false
  @State discoveryLoaded: boolean = false
  @State deleteTargetId: number = -1
  @State deleteTargetName: string = ''

  aboutToAppear(): void {
    this.ld()
  }

  async ld(): Promise<void> {
    this.loading = true
    this.err = ''
    try {
      let devicesPromise = getDevicesForUi()
      let roomsPromise = getRooms()
      this.devices = await devicesPromise
      this.rooms = await roomsPromise
      if (this.rooms.length > 0 && this.bindRoomId === 0) {
        this.bindRoomId = this.rooms[0].id
      }
    } catch (err) {
      let message = localizeMessage((err as Error).message, '加载设备列表失败')
      if (!this.initialLoadComplete) {
        this.err = message
      } else {
        try {
          this.getUIContext().getPromptAction().showToast({ message: message })
        } catch (_) {
        }
      }
    } finally {
      this.loading = false
      this.initialLoadComplete = true
    }
  }

  async scanCandidates(showSuccess: boolean = true): Promise<void> {
    if (this.scanning) {
      return
    }
    this.scanning = true
    try {
      this.discovered = await discoverDevices()
      this.discoveryLoaded = true
      if (showSuccess) {
        this.ok = this.discovered.length > 0 ? '候选设备列表已刷新' : '暂未发现新的候选设备'
      }
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '扫描候选设备失败')
    } finally {
      this.scanning = false
    }
  }

  async doDel(id: number): Promise<void> {
    if (this.deletingId > 0) {
      return
    }
    this.deletingId = id
    this.err = ''
    this.ok = ''
    try {
      await deleteDevice(id)
      this.ok = '设备已删除'
      await this.ld()
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '删除设备失败')
    } finally {
      this.deletingId = -1
      this.deleteTargetId = -1
      this.deleteTargetName = ''
    }
  }

  requestDelete(device: Device): void {
    this.deleteTargetId = device.id
    this.deleteTargetName = device.name
  }

  async confirmDelete(): Promise<void> {
    let id = this.deleteTargetId
    if (id > 0) {
      await this.doDel(id)
    }
  }

  async doSave(): Promise<void> {
    if (this.saving) {
      return
    }
    this.err = ''
    if (!this.en.trim()) {
      this.err = '设备名称不能为空'
      return
    }
    this.saving = true
    try {
      await updateDeviceName(this.eid, this.en.trim(), this.eb.trim())
      this.showEdit = false
      this.ok = '设备信息已更新'
      await this.ld()
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '保存设备信息失败')
    } finally {
      this.saving = false
    }
  }

  oe(device: Device): void {
    this.eid = device.id
    this.en = device.name
    this.eb = device.brand || ''
    this.showEdit = true
    this.err = ''
  }

  ob(candidate: DiscoveredDevice): void {
    this.bindTargetId = candidate.id
    this.bindName = candidate.name
    if (this.rooms.length > 0 && this.bindRoomId === 0) {
      this.bindRoomId = this.rooms[0].id
    }
    this.err = ''
    this.ok = ''
  }

  async doBind(candidate: DiscoveredDevice): Promise<void> {
    this.err = ''
    this.ok = ''
    if (this.bindRoomId === 0) {
      this.err = '请先选择房间'
      return
    }
    this.binding = true
    try {
      await bindDevice(candidate.id, this.bindRoomId, this.bindName.trim() || candidate.name)
      this.ok = '设备绑定成功'
      this.bindTargetId = ''
      this.bindName = ''
      await this.ld()
      await this.scanCandidates(false)
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '绑定设备失败')
    } finally {
      this.binding = false
    }
  }

  switchViewMode(mode: number): void {
    this.viewMode = mode
    if (mode === 1 && !this.discoveryLoaded && !this.scanning) {
      this.scanCandidates(false)
    }
  }

  @Builder roomSelector() {
    Scroll() {
      Row() {
        ForEach(this.rooms, (room: Room) => {
          Text(room.name)
            .fontSize(ControlCenterTheme.assistSize)
            .fontWeight(this.bindRoomId === room.id ? FontWeight.Bold : FontWeight.Medium)
            .fontColor(this.bindRoomId === room.id ? '#FFFFFF' : ControlCenterTheme.textSecondary)
            .height(ControlCenterTheme.tapTarget)
            .padding({ left: 14, right: 14, top: 12, bottom: 12 })
            .borderRadius(ControlCenterTheme.radiusChip)
            .backgroundColor(this.bindRoomId === room.id ? ControlCenterTheme.accent : ControlCenterTheme.surfaceMuted)
            .margin({ right: 8 })
          .onClick(() => { this.bindRoomId = room.id })
        }, (room: Room) => room.id.toString())
      }
    }
    .scrollable(ScrollDirection.Horizontal)
    .scrollBar(BarState.Off)
    .width('100%')
  }

  build() {
    Stack() {
      Column() {
        Row() {
        Column() {
          Text('设备')
            .fontSize(ControlCenterTheme.pageTitleSize)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('管理已绑定设备，或扫描并添加新设备')
            .fontSize(ControlCenterTheme.assistSize)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 4 })
        }
        .alignItems(HorizontalAlign.Start)
        Blank()
        Button() {
          Row() {
            SymbolGlyph($r('sys.symbol.magnifyingglass'))
              .fontSize(18)
              .fontColor([ControlCenterTheme.accent])
            Text(this.scanning ? '扫描中...' : '扫描')
              .fontSize(ControlCenterTheme.assistSize)
              .fontWeight(FontWeight.Bold)
              .fontColor(ControlCenterTheme.accent)
              .margin({ left: 5 })
          }
        }
          .type(ButtonType.Capsule)
          .height(ControlCenterTheme.tapTarget)
          .backgroundColor(ControlCenterTheme.accentSoft)
          .enabled(!this.scanning)
          .onClick(() => {
            this.viewMode = 1
            this.scanCandidates()
          })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 14, bottom: 12 })
      .alignItems(VerticalAlign.Center)

      this.buildDeviceTabs()

      if (this.ok) {
        StatusBanner({ message: this.ok, tone: 'success' })
          .margin({ top: 10, left: 16, right: 16 })
      }

      if (this.err) {
        StatusBanner({ message: this.err, detail: '请稍后重试', tone: 'danger' })
          .margin({ top: 10, left: 16, right: 16 })
      }

      if (this.loading && !this.initialLoadComplete) {
        Column() {
          LoadingProgress().width(28).height(28).color(ControlCenterTheme.accent)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
      } else {
        Scroll() {
          if (this.viewMode === 0) {
            this.buildBoundDevices()
          } else {
            this.buildCandidates()
          }
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)
      }

        AppBottomNav({ active: 'devices' })
      }
      .width('100%')
      .height('100%')

      if (this.showEdit) {
        this.Ed()
      }

      if (this.deleteTargetId > 0) {
        this.DeleteConfirm()
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(ControlCenterTheme.pageBg)
  }

  @Builder buildDeviceTabs() {
    Row() {
      this.deviceTab('已绑定', 0, () => this.switchViewMode(0))
      this.deviceTab('待绑定', 1, () => this.switchViewMode(1))
    }
    .width('100%')
    .padding(4)
    .borderRadius(ControlCenterTheme.radiusInner)
    .backgroundColor(ControlCenterTheme.surfaceMuted)
    .margin({ left: 16, right: 16 })
  }

  @Builder deviceTab(label: string, mode: number, action: () => void) {
    Text(label)
      .fontSize(13)
      .fontWeight(this.viewMode === mode ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(this.viewMode === mode ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary)
      .textAlign(TextAlign.Center)
      .layoutWeight(1)
      .height(ControlCenterTheme.tapTarget)
      .padding({ top: 13, bottom: 13 })
      .borderRadius(ControlCenterTheme.radiusPill)
      .backgroundColor(this.viewMode === mode ? ControlCenterTheme.surface : '#00000000')
      .border({ width: 1, color: this.viewMode === mode ? ControlCenterTheme.border : '#00000000' })
      .shadow(this.viewMode === mode ? { radius: 6, color: ControlCenterTheme.shadowSoft, offsetY: 2 } : { radius: 0, color: '#00000000', offsetY: 0 })
      .onClick(action)
  }

  @Builder buildBoundDevices() {
    Column() {
      if (this.devices.length === 0) {
        Column() {
          Text('还没有已绑定设备')
            .fontSize(ControlCenterTheme.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('切换到“待绑定”并扫描附近设备')
            .fontSize(ControlCenterTheme.assistSize)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 6 })
        }
        .width('100%')
        .padding({ top: 36, bottom: 36 })
      } else {
        ForEach(this.devices, (device: Device) => {
          Row() {
            Text(DeviceHelper.icon(device.type))
              .fontSize(22)
              .width(42)
              .height(42)
              .textAlign(TextAlign.Center)
              .padding({ top: 9 })
              .borderRadius(ControlCenterTheme.radiusInner)
              .backgroundColor(ControlCenterTheme.surfaceMuted)
            Column() {
              Text(device.name)
                .fontSize(ControlCenterTheme.bodySize)
                .fontWeight(FontWeight.Bold)
                .fontColor(ControlCenterTheme.textPrimary)
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
              Text(DeviceHelper.typeLabel(device.type) + ' · ' + (device.room_name || '未分配房间'))
                .fontSize(ControlCenterTheme.assistSize)
                .fontColor(ControlCenterTheme.textSecondary)
                .margin({ top: 4 })
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
              Text(device.online ? '在线 · ' + DeviceHelper.summaryText(device.status_summary, '状态正常') : '离线')
                .fontSize(ControlCenterTheme.assistSize)
                .fontColor(device.online ? ControlCenterTheme.success : ControlCenterTheme.textTertiary)
                .margin({ top: 5 })
                .maxLines(1)
                .textOverflow({ overflow: TextOverflow.Ellipsis })
            }
            .layoutWeight(1)
            .margin({ left: 12 })
            .alignItems(HorizontalAlign.Start)
            Button() {
              SymbolGlyph($r('sys.symbol.ai_edit'))
                .fontSize(20)
                .fontColor([DEVICE_ACTION_SECONDARY_FG])
            }
              .width(ControlCenterTheme.tapTarget)
              .height(ControlCenterTheme.tapTarget)
              .backgroundColor(DEVICE_ACTION_SECONDARY_BG)
              .borderRadius(ControlCenterTheme.radiusInner)
              .accessibilityText('编辑' + device.name)
              .onClick(() => this.oe(device))
            Button() {
              SymbolGlyph($r('sys.symbol.trash'))
                .fontSize(20)
                .fontColor([ControlCenterTheme.danger])
            }
              .width(ControlCenterTheme.tapTarget)
              .height(ControlCenterTheme.tapTarget)
              .backgroundColor(ControlCenterTheme.dangerSoft)
              .borderRadius(ControlCenterTheme.radiusInner)
              .margin({ left: 6 })
              .accessibilityText('删除' + device.name)
              .onClick(() => this.requestDelete(device))
          }
          .width('100%')
          .alignItems(VerticalAlign.Center)
          .padding(14)
          .borderRadius(ControlCenterTheme.radiusCard)
          .backgroundColor(ControlCenterTheme.surface)
          .border({ width: 1, color: ControlCenterTheme.border })
          .margin({ bottom: 10 })
        }, (device: Device) => device.id.toString())
      }
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 14, bottom: 20 })
  }

  @Builder buildCandidates() {
    Column() {
      if (this.rooms.length > 0) {
        Text('绑定到房间')
          .fontSize(ControlCenterTheme.assistSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textSecondary)
          .width('100%')
          .margin({ bottom: 8 })
        this.roomSelector()
      }

      if (this.discovered.length === 0) {
        Column() {
          Text('暂未发现可绑定设备')
            .fontSize(ControlCenterTheme.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('点击右上角“扫描”刷新列表')
            .fontSize(ControlCenterTheme.assistSize)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 6 })
        }
        .width('100%')
        .padding({ top: 40, bottom: 40 })
      } else {
        ForEach(this.discovered, (candidate: DiscoveredDevice) => {
          Column() {
            Row() {
              Text(DeviceHelper.icon(candidate.type)).fontSize(22)
              Column() {
                Text(candidate.name)
                  .fontSize(ControlCenterTheme.bodySize)
                  .fontWeight(FontWeight.Bold)
                  .fontColor(ControlCenterTheme.textPrimary)
                Text(DeviceHelper.typeLabel(candidate.type) + ' · ' + DeviceHelper.roomLabel(candidate))
                  .fontSize(ControlCenterTheme.assistSize)
                  .fontColor(ControlCenterTheme.textSecondary)
                  .margin({ top: 4 })
              }
              .layoutWeight(1)
              .margin({ left: 12 })
              .alignItems(HorizontalAlign.Start)
              Text(candidate.online ? '在线' : '离线')
                .fontSize(ControlCenterTheme.assistSize)
                .fontColor(candidate.online ? ControlCenterTheme.success : ControlCenterTheme.textTertiary)
            }
            .width('100%')
            .alignItems(VerticalAlign.Center)

            TextInput({
              text: this.bindTargetId === candidate.id ? this.bindName : candidate.name,
              placeholder: '设备显示名称'
            })
              .height(ControlCenterTheme.controlHeight)
              .borderRadius(ControlCenterTheme.radiusInner)
              .backgroundColor(ControlCenterTheme.surfaceMuted)
              .fontSize(ControlCenterTheme.bodySize)
              .padding({ left: 12, right: 12 })
              .margin({ top: 12 })
              .onFocus(() => this.ob(candidate))
              .onChange((value: string) => {
                this.bindTargetId = candidate.id
                this.bindName = value
              })

            Button(this.binding && this.bindTargetId === candidate.id ? '绑定中...' : '绑定设备')
              .width('100%')
              .height(ControlCenterTheme.tapTarget)
              .fontSize(ControlCenterTheme.bodySize)
              .fontWeight(FontWeight.Bold)
              .backgroundColor(DEVICE_ACTION_PRIMARY)
              .fontColor('#FFFFFF')
              .borderRadius(ControlCenterTheme.radiusInner)
              .enabled(!this.binding)
              .margin({ top: 10 })
              .onClick(() => {
                this.ob(candidate)
                this.doBind(candidate)
              })
          }
          .padding(14)
          .borderRadius(ControlCenterTheme.radiusCard)
          .backgroundColor(ControlCenterTheme.surface)
          .border({ width: 1, color: ControlCenterTheme.border })
          .margin({ top: 10 })
        }, (candidate: DiscoveredDevice) => candidate.id)
      }
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 14, bottom: 20 })
  }

  @Builder Ed() {
    Column() {
      Column() {
        Text('编辑设备').fontSize(ControlCenterTheme.sectionTitleSize).fontWeight(FontWeight.Bold).fontColor(ControlCenterTheme.textPrimary)
          .width('100%').textAlign(TextAlign.Center).margin({ bottom: 14 })
        Text('名称').fontSize(12).fontColor('#8C8C8C').width('100%').margin({ bottom: 4 })
        TextInput({ text: this.en, placeholder: '请输入设备名称' }).height(ControlCenterTheme.controlHeight).borderRadius(12).backgroundColor(ControlCenterTheme.surfaceMuted)
          .fontSize(14).padding({ left: 12 }).onChange((v: string) => { this.en = v })
        Text('品牌').fontSize(12).fontColor('#8C8C8C').width('100%').margin({ top: 10, bottom: 4 })
        TextInput({ text: this.eb, placeholder: '选填' }).height(ControlCenterTheme.controlHeight).borderRadius(12).backgroundColor(ControlCenterTheme.surfaceMuted)
          .fontSize(14).padding({ left: 12 }).onChange((v: string) => { this.eb = v })
        Row() {
          Button('取消').width('45%').height(ControlCenterTheme.tapTarget).fontSize(13).backgroundColor(DEVICE_ACTION_SECONDARY_BG)
            .fontColor(DEVICE_ACTION_SECONDARY_FG).borderRadius(12).onClick(() => { this.showEdit = false })
          Button(this.saving ? '保存中...' : '保存').width('45%').height(ControlCenterTheme.tapTarget).fontSize(13).backgroundColor(DEVICE_ACTION_PRIMARY)
            .fontColor('#FFFFFF').borderRadius(12).enabled(!this.saving).onClick(() => this.doSave())
        }
        .width('100%').justifyContent(FlexAlign.SpaceBetween).margin({ top: 14 })
      }
      .padding(18).borderRadius(ControlCenterTheme.radiusCard).backgroundColor(ControlCenterTheme.surface).width('85%')
    }
    .width('100%').height('100%').justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
    .backgroundColor(ControlCenterTheme.overlay)
  }

  @Builder DeleteConfirm() {
    Column() {
      Column() {
        Text('删除设备')
          .fontSize(ControlCenterTheme.sectionTitleSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        Text('确定删除“' + this.deleteTargetName + '”吗？删除后需要重新扫描并绑定。')
          .fontSize(ControlCenterTheme.bodySize)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 10 })
        Row() {
          Button('取消')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(ControlCenterTheme.bodySize)
            .fontColor(ControlCenterTheme.textPrimary)
            .backgroundColor(ControlCenterTheme.surfaceMuted)
            .borderRadius(ControlCenterTheme.radiusInner)
            .onClick(() => {
              this.deleteTargetId = -1
              this.deleteTargetName = ''
            })
          Blank().width(10)
          Button(this.deletingId > 0 ? '删除中...' : '确认删除')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(ControlCenterTheme.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
            .backgroundColor(ControlCenterTheme.danger)
            .borderRadius(ControlCenterTheme.radiusInner)
            .enabled(this.deletingId < 0)
            .onClick(() => this.confirmDelete())
        }
        .width('100%')
        .margin({ top: 18 })
      }
      .width('86%')
      .padding(20)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(ControlCenterTheme.overlay)
  }
}
