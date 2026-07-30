import { getDevicesForUi, getRooms, updateDeviceName, deleteDevice, discoverDevices, bindDevice } from '../common/ApiClient'
import { Room, Device, DiscoveredDevice } from '../model/DeviceModel'
import { UiText } from '../common/UiText'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { AppTopBar, AppBottomNav, StatusBanner, EmptyState, ConfirmPanel } from '../common/ControlCenterKit'

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
  @State showEdit: boolean = false
  @State showAddFlow: boolean = false
  @State pendingDeleteId: number = -1
  @State deletingId: number = -1
  @State eid: number = -1
  @State en: string = ''
  @State eb: string = ''
  @State bindRoomId: number = 0
  @State bindName: string = ''
  @State bindTargetId: string = ''
  @State err: string = ''
  @State ok: string = ''

  aboutToAppear(): void {
    this.ld()
  }

  async ld(): Promise<void> {
    this.loading = true
    this.err = ''
    try {
      this.devices = await getDevicesForUi()
      this.rooms = await getRooms()
      if (this.rooms.length > 0 && this.bindRoomId === 0) {
        this.bindRoomId = this.rooms[0].id
      }
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '加载设备列表失败')
    } finally {
      this.loading = false
    }
  }

  async scanCandidates(showSuccess: boolean = true): Promise<void> {
    if (this.scanning) {
      return
    }
    this.scanning = true
    try {
      this.discovered = await discoverDevices()
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
    if (this.deletingId >= 0) {
      return
    }
    this.deletingId = id
    this.pendingDeleteId = -1
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
    }
  }

  async doSave(): Promise<void> {
    this.err = ''
    if (!this.en.trim()) {
      this.err = '设备名称不能为空'
      return
    }
    try {
      await updateDeviceName(this.eid, this.en.trim(), this.eb.trim())
      this.showEdit = false
      this.ok = '设备信息已更新'
      await this.ld()
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '保存设备信息失败')
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
    if (this.binding) {
      return
    }
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
      if (this.showAddFlow === true) {
        await this.scanCandidates(false)
      }
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '绑定设备失败')
    } finally {
      this.binding = false
    }
  }

  @Builder roomSelector() {
    Scroll() {
      Row() {
        ForEach(this.rooms, (room: Room) => {
          Button(room.name)
            .height(ControlCenterTheme.tapTarget)
            .padding({ left: ControlCenterTheme.spaceMd, right: ControlCenterTheme.spaceMd })
            .fontSize(12)
            .fontWeight(this.bindRoomId === room.id ? FontWeight.Bold : FontWeight.Medium)
            .fontColor(this.bindRoomId === room.id ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary)
            .borderRadius(ControlCenterTheme.radiusInner)
            .backgroundColor(this.bindRoomId === room.id ? ControlCenterTheme.accentSoft : ControlCenterTheme.surfaceMuted)
            .margin({ right: ControlCenterTheme.spaceSm })
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
        AppTopBar({ title: '设备', subtitle: this.devices.length.toString() + ' 台已绑定', actionLabel: '添加设备', actionType: 'add',
        onAction: () => {
          this.showAddFlow = true
          this.scanCandidates(false)
        }
      })
        .padding({ left: ControlCenterTheme.gutter, right: ControlCenterTheme.gutter,
          top: ControlCenterTheme.spaceMd, bottom: ControlCenterTheme.spaceSm })

      if (this.ok) {
        StatusBanner({ message: this.ok, detail: '设备列表已更新', tone: 'success' })
          .margin({ top: ControlCenterTheme.spaceSm, left: ControlCenterTheme.gutter,
            right: ControlCenterTheme.gutter })
      }

      if (this.err) {
        StatusBanner({ message: this.err, detail: '请检查设置或网络连接', tone: 'danger' })
          .margin({ top: ControlCenterTheme.spaceSm, left: ControlCenterTheme.gutter,
            right: ControlCenterTheme.gutter })
      }

      if (this.loading) {
        Column() {
          LoadingProgress().width(28).height(28).color(ControlCenterTheme.accent)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
      } else {
        Scroll() {
          Column() {
            if (!this.showAddFlow) {
              Column() {
              Row() {
                Text('已绑定设备')
                  .fontSize(18)
                  .fontWeight(FontWeight.Bold)
                  .fontColor(ControlCenterTheme.textPrimary)
                Blank()
                Text(this.devices.length.toString() + ' 台')
                  .fontSize(12)
                  .fontColor(ControlCenterTheme.textSecondary)
              }
              .width('100%')
              .margin({ bottom: ControlCenterTheme.spaceMd })

              if (this.devices.length === 0) {
                EmptyState({
                  title: '还没有已绑定设备',
                  detail: '使用右上角的添加设备入口开始绑定。'
                })
              } else {
                ForEach(this.devices, (device: Device) => {
                  Column() {
                    Row() {
                      Text(DeviceHelper.icon(device.type))
                        .width(ControlCenterTheme.tapTarget)
                        .height(ControlCenterTheme.tapTarget)
                        .fontSize(18)
                        .fontWeight(FontWeight.Bold)
                        .fontColor(ControlCenterTheme.accent)
                        .textAlign(TextAlign.Center)
                        .padding({ top: ControlCenterTheme.spaceMd })
                        .borderRadius(ControlCenterTheme.radiusInner)
                        .backgroundColor(ControlCenterTheme.accentSoft)
                      Column() {
                        Text(device.name)
                          .fontSize(15)
                          .fontWeight(FontWeight.Bold)
                          .fontColor(ControlCenterTheme.textPrimary)
                        Text(DeviceHelper.typeLabel(device.type) + ' · ' + (device.room_name || '未分配房间'))
                          .fontSize(12)
                          .fontColor(ControlCenterTheme.textSecondary)
                          .margin({ top: ControlCenterTheme.spaceXs })
                        Text(device.online ? '在线' : '离线')
                          .fontSize(12)
                          .fontWeight(FontWeight.Medium)
                          .fontColor(device.online ? ControlCenterTheme.success : ControlCenterTheme.danger)
                          .margin({ top: ControlCenterTheme.spaceXs })
                      }
                      .layoutWeight(1)
                      .margin({ left: ControlCenterTheme.spaceMd })
                      .alignItems(HorizontalAlign.Start)
                    }
                    .width('100%')
                    .alignItems(VerticalAlign.Center)

                    Text(DeviceHelper.summaryText(device.status_summary, '暂无最近状态'))
                      .width('100%')
                      .fontSize(12)
                      .fontColor(ControlCenterTheme.textSecondary)
                      .margin({ top: ControlCenterTheme.spaceMd })
                      .maxLines(2)
                      .textOverflow({ overflow: TextOverflow.Ellipsis })
                    Text(DeviceHelper.seenText(device.last_seen_at, '等待首次上报'))
                      .width('100%')
                      .fontSize(11)
                      .fontColor(ControlCenterTheme.textTertiary)
                      .margin({ top: ControlCenterTheme.spaceXs })

                    Row() {
                      Button('编辑')
                        .layoutWeight(1)
                        .height(ControlCenterTheme.tapTarget)
                        .fontSize(13)
                        .fontColor(ControlCenterTheme.textPrimary)
                        .backgroundColor(ControlCenterTheme.surfaceMuted)
                        .borderRadius(ControlCenterTheme.radiusInner)
                        .enabled(this.deletingId < 0)
                        .onClick(() => this.oe(device))
                      Blank().width(ControlCenterTheme.spaceSm)
                      Button(this.deletingId === device.id ? '删除中...' : '删除')
                        .layoutWeight(1)
                        .height(ControlCenterTheme.tapTarget)
                        .fontSize(13)
                        .fontColor(ControlCenterTheme.danger)
                        .backgroundColor(ControlCenterTheme.dangerSoft)
                        .borderRadius(ControlCenterTheme.radiusInner)
                        .enabled(this.deletingId < 0)
                        .onClick(() => { this.pendingDeleteId = device.id })
                    }
                    .width('100%')
                    .margin({ top: ControlCenterTheme.spaceMd })
                  }
                  .width('100%')
                  .padding(ControlCenterTheme.spaceLg)
                  .borderRadius(ControlCenterTheme.radiusCard)
                  .backgroundColor(ControlCenterTheme.surface)
                  .border({ width: 1, color: ControlCenterTheme.border })
                  .margin({ bottom: ControlCenterTheme.spaceSm })
                }, (device: Device) => device.id.toString())
              }
              }
              .width('100%')
            }

            if (this.showAddFlow) {
              Column() {
                Row() {
                  Column() {
                    Text('添加设备')
                      .fontSize(18)
                      .fontWeight(FontWeight.Bold)
                      .fontColor(ControlCenterTheme.textPrimary)
                    Text('选择候选设备并绑定到房间')
                      .fontSize(12)
                      .fontColor(ControlCenterTheme.textSecondary)
                      .margin({ top: ControlCenterTheme.spaceXs })
                  }
                  .layoutWeight(1)
                  .alignItems(HorizontalAlign.Start)
                  Button('完成')
                    .height(ControlCenterTheme.tapTarget)
                    .padding({ left: ControlCenterTheme.spaceLg, right: ControlCenterTheme.spaceLg })
                    .fontSize(13)
                    .fontColor(ControlCenterTheme.textPrimary)
                    .backgroundColor(ControlCenterTheme.surfaceMuted)
                    .borderRadius(ControlCenterTheme.radiusInner)
                    .onClick(() => { this.showAddFlow = false })
                }
                .width('100%')
                .alignItems(VerticalAlign.Center)

                Row() {
                  Text('候选设备')
                    .fontSize(15)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(ControlCenterTheme.textPrimary)
                  Text(this.discovered.length.toString() + ' 台')
                    .fontSize(12)
                    .fontColor(ControlCenterTheme.textSecondary)
                    .margin({ left: ControlCenterTheme.spaceSm })
                  Blank()
                  Button(this.scanning ? '扫描中...' : '重新扫描')
                    .height(ControlCenterTheme.tapTarget)
                    .padding({ left: ControlCenterTheme.spaceMd, right: ControlCenterTheme.spaceMd })
                    .fontSize(12)
                    .fontColor(ControlCenterTheme.accent)
                    .backgroundColor(ControlCenterTheme.accentSoft)
                    .borderRadius(ControlCenterTheme.radiusInner)
                    .enabled(!this.scanning)
                    .onClick(() => this.scanCandidates())
                }
                .width('100%')
                .alignItems(VerticalAlign.Center)
                .margin({ top: ControlCenterTheme.spaceLg, bottom: ControlCenterTheme.spaceMd })

                if (this.rooms.length > 0) {
                  Text('绑定到房间')
                    .width('100%')
                    .fontSize(12)
                    .fontWeight(FontWeight.Medium)
                    .fontColor(ControlCenterTheme.textPrimary)
                    .margin({ bottom: ControlCenterTheme.spaceSm })
                  this.roomSelector()
                } else {
                  StatusBanner({ message: '暂无可用房间', detail: '请先创建房间再绑定设备', tone: 'warning' })
                }

                if (this.discovered.length === 0) {
                  EmptyState({
                    title: this.scanning ? '正在扫描候选设备' : '暂未发现候选设备',
                    detail: this.scanning ? '发现结果会自动显示在这里。' : '确认设备在线后重新扫描。',
                    actionLabel: this.scanning ? '扫描中...' : '重新扫描',
                    actionEnabled: !this.scanning,
                    onAction: () => this.scanCandidates()
                  })
                    .margin({ top: ControlCenterTheme.spaceMd })
                } else {
                  ForEach(this.discovered, (candidate: DiscoveredDevice) => {
                    Column() {
                      Row() {
                        Text(DeviceHelper.icon(candidate.type))
                          .width(ControlCenterTheme.tapTarget)
                          .height(ControlCenterTheme.tapTarget)
                          .fontSize(18)
                          .fontWeight(FontWeight.Bold)
                          .fontColor(ControlCenterTheme.accent)
                          .textAlign(TextAlign.Center)
                          .padding({ top: ControlCenterTheme.spaceMd })
                          .borderRadius(ControlCenterTheme.radiusInner)
                          .backgroundColor(ControlCenterTheme.accentSoft)
                        Column() {
                          Text(candidate.name)
                            .fontSize(15)
                            .fontWeight(FontWeight.Bold)
                            .fontColor(ControlCenterTheme.textPrimary)
                          Text(DeviceHelper.typeLabel(candidate.type) + ' · ' + DeviceHelper.roomLabel(candidate))
                            .fontSize(12)
                            .fontColor(ControlCenterTheme.textSecondary)
                            .margin({ top: ControlCenterTheme.spaceXs })
                        }
                        .layoutWeight(1)
                        .margin({ left: ControlCenterTheme.spaceMd })
                        .alignItems(HorizontalAlign.Start)
                        Text(candidate.online ? '在线' : '离线')
                          .fontSize(12)
                          .fontWeight(FontWeight.Medium)
                          .fontColor(candidate.online ? ControlCenterTheme.success : ControlCenterTheme.danger)
                      }
                      .width('100%')
                      .alignItems(VerticalAlign.Center)

                      Text(DeviceHelper.summaryText(candidate.status_summary, '暂无最近状态'))
                        .width('100%')
                        .fontSize(12)
                        .fontColor(ControlCenterTheme.textSecondary)
                        .margin({ top: ControlCenterTheme.spaceMd })
                        .maxLines(2)
                        .textOverflow({ overflow: TextOverflow.Ellipsis })
                      Text(DeviceHelper.seenText(candidate.last_seen_at, '刚刚发现'))
                        .width('100%')
                        .fontSize(11)
                        .fontColor(ControlCenterTheme.textTertiary)
                        .margin({ top: ControlCenterTheme.spaceXs })

                      Text('设备名称')
                        .width('100%')
                        .fontSize(12)
                        .fontWeight(FontWeight.Medium)
                        .fontColor(ControlCenterTheme.textPrimary)
                        .margin({ top: ControlCenterTheme.spaceMd, bottom: ControlCenterTheme.spaceSm })
                      TextInput({
                        text: this.bindTargetId === candidate.id ? this.bindName : candidate.name,
                        placeholder: '请输入设备显示名称'
                      })
                        .height(ControlCenterTheme.controlHeight)
                        .borderRadius(ControlCenterTheme.radiusInner)
                        .backgroundColor(ControlCenterTheme.surfaceMuted)
                        .fontSize(14)
                        .padding({ left: ControlCenterTheme.spaceMd, right: ControlCenterTheme.spaceMd })
                        .onFocus(() => this.ob(candidate))
                        .onChange((value: string) => {
                          this.bindTargetId = candidate.id
                          this.bindName = value
                        })

                      Row() {
                        Text(this.bindRoomId === 0 ? '请先选择绑定房间' : '将绑定到所选房间')
                          .fontSize(12)
                          .fontColor(ControlCenterTheme.textSecondary)
                          .layoutWeight(1)
                        Button(this.binding && this.bindTargetId === candidate.id ? '绑定中...' : '绑定')
                          .height(ControlCenterTheme.tapTarget)
                          .padding({ left: ControlCenterTheme.spaceLg, right: ControlCenterTheme.spaceLg })
                          .fontSize(13)
                          .fontColor(ControlCenterTheme.surface)
                          .backgroundColor(ControlCenterTheme.accent)
                          .borderRadius(ControlCenterTheme.radiusInner)
                          .enabled(!this.binding)
                          .onClick(() => {
                            if (this.bindTargetId !== candidate.id) {
                              this.ob(candidate)
                            }
                            this.doBind(candidate)
                          })
                      }
                      .width('100%')
                      .alignItems(VerticalAlign.Center)
                      .margin({ top: ControlCenterTheme.spaceMd })
                    }
                    .width('100%')
                    .padding(ControlCenterTheme.spaceLg)
                    .borderRadius(ControlCenterTheme.radiusCard)
                    .backgroundColor(ControlCenterTheme.surface)
                    .border({ width: 1, color: ControlCenterTheme.border })
                    .margin({ top: ControlCenterTheme.spaceSm })
                  }, (candidate: DiscoveredDevice) => candidate.id)
                }
              }
              .width('100%')
              .margin({ top: ControlCenterTheme.spaceXl })
            }
          }
          .width('100%')
          .padding({ left: ControlCenterTheme.gutter, right: ControlCenterTheme.gutter,
            top: ControlCenterTheme.spaceMd, bottom: ControlCenterTheme.spaceXl })
        }
        .layoutWeight(1).scrollBar(BarState.Off)
      }

        AppBottomNav({ active: 'devices' })
      }
      .width('100%')
      .height('100%')

      if (this.showEdit) {
        this.Ed()
      }

      if (this.pendingDeleteId > 0) {
        Column() {
          ConfirmPanel({
            title: '删除设备？',
            detail: '删除后需要重新添加并绑定该设备。',
            confirmLabel: '确认删除',
            cancelLabel: '取消',
            onCancel: () => { this.pendingDeleteId = -1 },
            onConfirm: () => this.doDel(this.pendingDeleteId)
          })
        }
        .width('100%')
        .height('100%')
        .padding(ControlCenterTheme.gutter)
        .justifyContent(FlexAlign.Center)
        .alignItems(HorizontalAlign.Center)
        .backgroundColor(ControlCenterTheme.overlay)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(ControlCenterTheme.pageBg)
  }

  @Builder Ed() {
    Column() {
      Column() {
        Text('编辑设备')
          .width('100%')
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
          .textAlign(TextAlign.Start)
          .margin({ bottom: ControlCenterTheme.spaceLg })
        Text('名称')
          .width('100%')
          .fontSize(12)
          .fontWeight(FontWeight.Medium)
          .fontColor(ControlCenterTheme.textPrimary)
          .margin({ bottom: ControlCenterTheme.spaceSm })
        TextInput({ text: this.en, placeholder: '请输入设备名称' })
          .height(ControlCenterTheme.controlHeight)
          .borderRadius(ControlCenterTheme.radiusInner)
          .backgroundColor(ControlCenterTheme.surfaceMuted)
          .fontSize(14)
          .padding({ left: ControlCenterTheme.spaceMd, right: ControlCenterTheme.spaceMd })
          .onChange((v: string) => { this.en = v })
        Text('品牌')
          .width('100%')
          .fontSize(12)
          .fontWeight(FontWeight.Medium)
          .fontColor(ControlCenterTheme.textPrimary)
          .margin({ top: ControlCenterTheme.spaceMd, bottom: ControlCenterTheme.spaceSm })
        TextInput({ text: this.eb, placeholder: '选填' })
          .height(ControlCenterTheme.controlHeight)
          .borderRadius(ControlCenterTheme.radiusInner)
          .backgroundColor(ControlCenterTheme.surfaceMuted)
          .fontSize(14)
          .padding({ left: ControlCenterTheme.spaceMd, right: ControlCenterTheme.spaceMd })
          .onChange((v: string) => { this.eb = v })
        Row() {
          Button('取消')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(13)
            .fontColor(ControlCenterTheme.textPrimary)
            .backgroundColor(ControlCenterTheme.surfaceMuted)
            .borderRadius(ControlCenterTheme.radiusInner)
            .onClick(() => { this.showEdit = false })
          Blank().width(ControlCenterTheme.spaceSm)
          Button('保存')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(13)
            .fontColor(ControlCenterTheme.surface)
            .backgroundColor(ControlCenterTheme.accent)
            .borderRadius(ControlCenterTheme.radiusInner)
            .onClick(() => this.doSave())
        }
        .width('100%')
        .margin({ top: ControlCenterTheme.spaceLg })
      }
      .width('88%')
      .padding(ControlCenterTheme.spaceLg)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(ControlCenterTheme.overlay)
    .onClick(() => { this.showEdit = false })
  }
}
