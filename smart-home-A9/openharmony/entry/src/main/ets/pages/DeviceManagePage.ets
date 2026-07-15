import { getDevicesForUi, getRooms, updateDeviceName, deleteDevice, discoverDevices, bindDevice } from '../common/ApiClient'
import { Room, Device, DiscoveredDevice } from '../model/DeviceModel'
import { UiText } from '../common/UiText'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { AppBottomNav } from '../common/ControlCenterKit'

const DEVICE_ACTION_PRIMARY: string = '#111111'
const DEVICE_ACTION_SECONDARY_BG: string = '#EEEEEE'
const DEVICE_ACTION_SECONDARY_FG: string = '#111111'

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
  @State showEdit: boolean = false
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
      await this.scanCandidates(false)
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '加载设备列表失败')
    } finally {
      this.loading = false
    }
  }

  async scanCandidates(showSuccess: boolean = true): Promise<void> {
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
    this.err = ''
    this.ok = ''
    try {
      await deleteDevice(id)
      this.ok = '设备已删除'
      await this.ld()
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '删除设备失败')
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
          Column() {
            Text(room.name).fontSize(11).fontColor(this.bindRoomId === room.id ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary)
              .padding({ left: 8, right: 8, top: 4, bottom: 4 }).borderRadius(6)
              .backgroundColor(this.bindRoomId === room.id ? ControlCenterTheme.accentSoft : ControlCenterTheme.surfaceMuted).margin({ right: 6 })
          }
          .onClick(() => { this.bindRoomId = room.id })
        }, (room: Room) => room.id.toString())
      }
    }
    .scrollable(ScrollDirection.Horizontal).scrollBar(BarState.Off).width('100%')
  }

  build() {
    Column() {
      Row() {
        Text('\u2190').fontSize(18).fontColor(ControlCenterTheme.textPrimary).padding(8).onClick(() => this.getUIContext().getRouter().back())
        Text('设备管理').fontSize(17).fontWeight(FontWeight.Bold).fontColor(ControlCenterTheme.textPrimary)
        Blank()
        Text(this.scanning ? '扫描中...' : '扫描').fontSize(14).fontColor(ControlCenterTheme.accent).onClick(() => {
          if (!this.scanning) {
            this.scanCandidates()
          }
        })
      }
      .width('100%').height(48).padding({ left: 14, right: 14 }).alignItems(VerticalAlign.Center)
      .backgroundColor(ControlCenterTheme.surface).border({ width: { bottom: 0.5 }, color: ControlCenterTheme.border })

      if (this.ok) {
        Text(this.ok).fontSize(13).fontColor(ControlCenterTheme.accent).padding(8).borderRadius(10)
          .backgroundColor(ControlCenterTheme.accentSoft).margin({ top: 8, left: 14, right: 14 })
      }

      if (this.err) {
        Text(this.err).fontSize(13).fontColor('#A14D4D').padding(8).borderRadius(10)
          .backgroundColor(ControlCenterTheme.dangerSoft).margin({ top: 8, left: 14, right: 14 })
      }

      if (this.loading) {
        Column() {
          LoadingProgress().width(28).height(28).color(ControlCenterTheme.accent)
        }
        .width('100%').layoutWeight(1).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
      } else {
        Scroll() {
          Column() {
            Column() {
              Row() {
                Text('已绑定设备').fontSize(15).fontWeight(FontWeight.Bold).fontColor(ControlCenterTheme.textPrimary)
                Blank()
                Text(this.devices.length.toString()).fontSize(12).fontColor('#8C8C8C')
              }
              .width('100%').margin({ bottom: 10 })

              if (this.devices.length === 0) {
                Column() {
                  Text('当前还没有已绑定设备').fontSize(13).fontColor('#B0B0B0')
                }
                .width('100%').height(80).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
              } else {
                ForEach(this.devices, (device: Device) => {
                  Row() {
                    Text(DeviceHelper.icon(device.type)).fontSize(22)
                    Column() {
                      Text(device.name).fontSize(14).fontWeight(FontWeight.Bold).fontColor('#3D3D3D')
                      Row() {
                        Text(DeviceHelper.typeLabel(device.type)).fontSize(11).fontColor('#8C8C8C')
                        Text(' · ' + (device.room_name || '未分配房间')).fontSize(11).fontColor('#8C8C8C')
                      }
                      .margin({ top: 2 })
                      Text(device.online ? '在线' : '离线').fontSize(11).fontColor(device.online ? '#8FBF7F' : '#D49595')
                        .margin({ top: 4 })
                      Text(DeviceHelper.summaryText(device.status_summary, '暂无最近状态')).fontSize(11).fontColor('#8C8C8C')
                        .margin({ top: 2 }).maxLines(2).textOverflow({ overflow: TextOverflow.Ellipsis })
                      Text(DeviceHelper.seenText(device.last_seen_at, '等待首次上报')).fontSize(10).fontColor('#B0B0B0')
                        .margin({ top: 4 })
                    }
                    .layoutWeight(1).margin({ left: 12 }).alignItems(HorizontalAlign.Start)
                    Text('编辑').fontSize(11).fontColor(DEVICE_ACTION_SECONDARY_FG).padding({ left: 8, right: 8, top: 5, bottom: 5 })
                      .borderRadius(10).backgroundColor(DEVICE_ACTION_SECONDARY_BG).onClick(() => this.oe(device)).margin({ right: 6 })
                    Text('删除').fontSize(11).fontColor('#FFFFFF').padding({ left: 8, right: 8, top: 5, bottom: 5 })
                      .borderRadius(10).backgroundColor(DEVICE_ACTION_PRIMARY).onClick(() => this.doDel(device.id))
                  }
                  .width('100%').alignItems(VerticalAlign.Center).padding(12).borderRadius(10)
                  .backgroundColor(ControlCenterTheme.surface).margin({ bottom: 8 })
                }, (device: Device) => device.id.toString())
              }
            }
            .padding(14).borderRadius(ControlCenterTheme.radiusCard).backgroundColor(ControlCenterTheme.surfaceMuted).margin({ left: 14, right: 14, top: 14 })

            Column() {
              Row() {
                Text('候选设备').fontSize(15).fontWeight(FontWeight.Bold).fontColor(ControlCenterTheme.textPrimary)
                Blank()
                if (this.scanning) {
                  LoadingProgress().width(18).height(18).color(ControlCenterTheme.accent)
                } else {
                  Text(this.discovered.length.toString()).fontSize(12).fontColor('#8C8C8C')
                }
              }
              .width('100%').margin({ bottom: 10 })

              if (this.rooms.length > 0) {
                Text('绑定到房间').fontSize(12).fontColor('#8C8C8C').width('100%').margin({ bottom: 6 })
                this.roomSelector()
              }

              if (this.discovered.length === 0) {
                Column() {
                  Text('当前没有可用的候选设备').fontSize(13).fontColor('#B0B0B0')
                  Text('点击“扫描”刷新候选设备列表').fontSize(11).fontColor('#C0C0C0').margin({ top: 4 })
                }
                .width('100%').height(90).justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
              } else {
                ForEach(this.discovered, (candidate: DiscoveredDevice) => {
                  Column() {
                    Row() {
                      Text(DeviceHelper.icon(candidate.type)).fontSize(22)
                      Column() {
                        Text(candidate.name).fontSize(14).fontWeight(FontWeight.Bold).fontColor('#3D3D3D')
                        Row() {
                          Text(DeviceHelper.typeLabel(candidate.type)).fontSize(11).fontColor('#8C8C8C')
                          Text(' · ' + DeviceHelper.roomLabel(candidate)).fontSize(11).fontColor('#8C8C8C')
                        }
                        .margin({ top: 2 })
                      }
                      .layoutWeight(1).margin({ left: 12 }).alignItems(HorizontalAlign.Start)
                      Text(candidate.online ? '在线' : '离线').fontSize(11).fontColor(candidate.online ? '#8FBF7F' : '#D49595')
                        .padding({ left: 8, right: 8, top: 3, bottom: 3 }).borderRadius(4)
                        .backgroundColor(candidate.online ? '#8FBF7F15' : '#D4959515')
                    }
                    .width('100%').alignItems(VerticalAlign.Center)

                    Text(DeviceHelper.summaryText(candidate.status_summary, '暂无最近状态')).fontSize(11).fontColor('#8C8C8C')
                      .width('100%').margin({ top: 8 }).maxLines(2).textOverflow({ overflow: TextOverflow.Ellipsis })
                    Text(DeviceHelper.seenText(candidate.last_seen_at, '刚刚发现')).fontSize(10).fontColor('#B0B0B0')
                      .width('100%').margin({ top: 4 })

                    TextInput({
                      text: this.bindTargetId === candidate.id ? this.bindName : candidate.name,
                      placeholder: '请输入设备显示名称'
                    })
                      .height(40).borderRadius(12).backgroundColor(ControlCenterTheme.surfaceMuted).fontSize(13)
                      .padding({ left: 12 }).margin({ top: 10 })
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
                        .height(ControlCenterTheme.tapTarget).fontSize(12).backgroundColor(DEVICE_ACTION_PRIMARY).fontColor('#FFFFFF')
                        .borderRadius(12).enabled(!this.binding || this.bindTargetId !== candidate.id)
                        .onClick(() => {
                          this.ob(candidate)
                          this.doBind(candidate)
                        })
                    }
                    .width('100%').alignItems(VerticalAlign.Center).margin({ top: 10 })
                  }
                  .padding(12).borderRadius(ControlCenterTheme.radiusInner).backgroundColor(ControlCenterTheme.surface).margin({ bottom: 8 })
                }, (candidate: DiscoveredDevice) => candidate.id)
              }
            }
            .padding(14).borderRadius(ControlCenterTheme.radiusCard).backgroundColor(ControlCenterTheme.surfaceMuted).margin({ left: 14, right: 14, top: 14, bottom: 18 })
          }
        }
        .layoutWeight(1).scrollBar(BarState.Off)
      }

      AppBottomNav({ active: 'devices' })

      if (this.showEdit) {
        this.Ed()
      }
    }
    .width('100%').height('100%').backgroundColor(ControlCenterTheme.pageBg)
  }

  @Builder Ed() {
    Column() {
      Column() {
        Text('编辑设备').fontSize(16).fontWeight(FontWeight.Bold).fontColor(ControlCenterTheme.textPrimary)
          .width('100%').textAlign(TextAlign.Center).margin({ bottom: 14 })
        Text('名称').fontSize(12).fontColor('#8C8C8C').width('100%').margin({ bottom: 4 })
        TextInput({ text: this.en, placeholder: '请输入设备名称' }).height(40).borderRadius(12).backgroundColor(ControlCenterTheme.surfaceMuted)
          .fontSize(14).padding({ left: 12 }).onChange((v: string) => { this.en = v })
        Text('品牌').fontSize(12).fontColor('#8C8C8C').width('100%').margin({ top: 10, bottom: 4 })
        TextInput({ text: this.eb, placeholder: '选填' }).height(40).borderRadius(12).backgroundColor(ControlCenterTheme.surfaceMuted)
          .fontSize(14).padding({ left: 12 }).onChange((v: string) => { this.eb = v })
        Row() {
          Button('取消').width('45%').height(38).fontSize(13).backgroundColor(DEVICE_ACTION_SECONDARY_BG)
            .fontColor(DEVICE_ACTION_SECONDARY_FG).borderRadius(12).onClick(() => { this.showEdit = false })
          Button('保存').width('45%').height(38).fontSize(13).backgroundColor(DEVICE_ACTION_PRIMARY)
            .fontColor('#FFFFFF').borderRadius(12).onClick(() => this.doSave())
        }
        .width('100%').justifyContent(FlexAlign.SpaceBetween).margin({ top: 14 })
      }
      .padding(18).borderRadius(ControlCenterTheme.radiusCard).backgroundColor(ControlCenterTheme.surface).width('85%')
    }
    .width('100%').height('100%').justifyContent(FlexAlign.Center).alignItems(HorizontalAlign.Center)
    .backgroundColor('#40000000').onClick(() => { this.showEdit = false })
  }
}
