/**
 * 仪表盘 — 总览所有房间设备状态
 */
import { router } from '@kit.ArkUI'
import { getRooms, getDevices, sendCommand, getToken } from '../common/ApiClient'
import { connectWS, disconnectWS } from '../common/MqttClient'
import { Room, Device, DeviceStatus } from '../model/DeviceModel'

@Entry
@Component
struct DashboardPage {
  @State rooms: Room[] = []
  @State devices: Device[] = []
  @State currentRoom: number = 0 // 0=全部
  @State wsConnected: boolean = false
  @State sensorData: Record<string, string | number> = {} // 温湿度缓存

  aboutToAppear() {
    this.loadData()
    // 连接 WebSocket
    connectWS((msg: Object) => {
      this.onWSMessage(msg)
    })
    this.wsConnected = true
  }

  aboutToDisappear() {
    disconnectWS()
  }

  async loadData() {
    try {
      this.rooms = await getRooms() as Room[]
      this.devices = await getDevices() as Device[]
    } catch (err) {
      console.error('加载数据失败', err)
    }
  }

  onWSMessage(msg: Object) {
    const m = msg as Record<string, Object>
    if (m['type'] === 'sensor_update') {
      const data = m['data'] as Record<string, number>
      if (data) {
        Object.keys(data).forEach(key => {
          this.sensorData[key] = data[key]
        })
      }
    }
  }

  getDevicesByRoom(roomId: number): Device[] {
    if (roomId === 0) return this.devices
    return this.devices.filter(d => d.room_id === roomId)
  }

  getStatusText(device: Device): string {
    try {
      const status: DeviceStatus = JSON.parse(device.status_json || '{}')
      switch (device.type) {
        case 'light':
          return status.power === 'on' ? `开启 · 亮度${status.brightness}%` : '关闭'
        case 'ac':
          return status.power === 'on' ? `${status.mode} · ${status.temp}°C` : '关闭'
        case 'door_lock':
          return status.locked ? '已锁定' : '已解锁'
        case 'temperature_sensor':
          return `${status.value || '--'}°C`
        case 'humidity_sensor':
          return `${status.value || '--'}%`
        case 'pir_sensor':
          return status.presence ? '有人' : '无人'
        default:
          return '--'
      }
    } catch {
      return '--'
    }
  }

  getDeviceIcon(device: Device): Resource {
    switch (device.type) {
      case 'light': return $r('sys.media.ohos_ic_public_light')
      case 'ac': return $r('sys.media.ohos_ic_public_ac')
      case 'door_lock': return $r('sys.media.ohos_ic_public_lock')
      case 'temperature_sensor': return $r('sys.media.ohos_ic_public_temperature')
      case 'humidity_sensor': return $r('sys.media.ohos_ic_public_humidity')
      case 'pir_sensor': return $r('sys.media.ohos_ic_public_person')
      default: return $r('sys.media.ohos_ic_public_device')
    }
  }

  build() {
    Column() {
      // 顶部栏
      Row() {
        Text('智能家居')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)

        Row() {
          Text(this.wsConnected ? '● 已连接' : '○ 断开')
            .fontSize(12)
            .fontColor(this.wsConnected ? '#4CAF50' : '#F44336')
        }
      }
      .width('100%')
      .height(56)
      .padding({ left: 16, right: 16 })
      .justifyContent(FlexAlign.SpaceBetween)
      .alignItems(VerticalAlign.Center)
      .linearGradient({
        direction: GradientDirection.Right,
        colors: [['#1A3C6E', 0.0], ['#2B579A', 1.0]]
      })

      // 房间切换 Tabs
      Row() {
        Scroll() {
          Row() {
            this.RoomTab(0, '全部')
            ForEach(this.rooms, (room: Room) => {
              this.RoomTab(room.id, room.name)
            })
          }
          .space(8)
        }
        .scrollable(ScrollDirection.Horizontal)
        .width('100%')
      }
      .padding({ left: 16, right: 16, top: 12, bottom: 8 })

      // 设备卡片列表
      Scroll() {
        Column() {
          // 温湿度概览
          if (this.sensorData['temperature'] || this.sensorData['humidity']) {
            Row() {
              this.SensorCard('温度', `${this.sensorData['temperature'] || '--'}°C`, '#FF9800')
              this.SensorCard('湿度', `${this.sensorData['humidity'] || '--'}%`, '#2196F3')
            }
            .width('100%')
            .space(12)
            .margin({ bottom: 12 })
          }

          // 设备网格
          GridRow({ columns: 2, gutter: 12 }) {
            ForEach(this.getDevicesByRoom(this.currentRoom), (device: Device) => {
              GridCol() {
                this.DeviceCard(device)
              }
            })
          }
        }
        .padding(16)
      }
      .layoutWeight(1)
      .scrollBar(BarState.Off)

      // 底部导航
      Row() {
        this.NavItem('总览', true)
        this.NavItem('照明', false, () => router.pushUrl({ url: 'pages/LightControlPage' }))
        this.NavItem('空调', false, () => router.pushUrl({ url: 'pages/ACControlPage' }))
        this.NavItem('门禁', false, () => router.pushUrl({ url: 'pages/DoorLockPage' }))
      }
      .width('100%')
      .height(56)
      .backgroundColor(Color.White)
      .border({ width: { top: 0.5 }, color: '#E0E0E0' })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }

  @Builder
  RoomTab(id: number, name: string) {
    Text(name)
      .fontSize(14)
      .fontColor(this.currentRoom === id ? '#1A3C6E' : '#666')
      .fontWeight(this.currentRoom === id ? FontWeight.Bold : FontWeight.Normal)
      .padding({ left: 16, right: 16, top: 8, bottom: 8 })
      .borderRadius(20)
      .backgroundColor(this.currentRoom === id ? '#E8EEF5' : 'transparent')
      .onClick(() => { this.currentRoom = id })
  }

  @Builder
  SensorCard(title: string, value: string, color: string) {
    Column() {
      Text(title)
        .fontSize(12)
        .fontColor('#999')
      Text(value)
        .fontSize(22)
        .fontWeight(FontWeight.Bold)
        .fontColor(color)
        .margin({ top: 4 })
    }
    .layoutWeight(1)
    .padding(16)
    .borderRadius(12)
    .backgroundColor(Color.White)
    .alignItems(HorizontalAlign.Center)
    .shadow({ radius: 4, color: '#1A000000', offsetY: 2 })
  }

  @Builder
  DeviceCard(device: Device) {
    Column() {
      Row() {
        Text(this.getDeviceIcon(device))
          .fontSize(20)
        Blank()
        Text(device.type.includes('sensor') ? '传感器' : '可控')
          .fontSize(10)
          .fontColor('#999')
      }
      .width('100%')

      Text(device.name)
        .fontSize(14)
        .fontWeight(FontWeight.Medium)
        .fontColor('#333')
        .margin({ top: 12 })

      Text(this.getStatusText(device))
        .fontSize(13)
        .fontColor('#666')
        .margin({ top: 4 })
    }
    .padding(16)
    .borderRadius(12)
    .backgroundColor(Color.White)
    .shadow({ radius: 4, color: '#1A000000', offsetY: 2 })
    .onClick(() => {
      // 根据设备类型跳转
      if (device.type === 'light') {
        router.pushUrl({ url: 'pages/LightControlPage' })
      } else if (device.type === 'ac') {
        router.pushUrl({ url: 'pages/ACControlPage' })
      } else if (device.type === 'door_lock') {
        router.pushUrl({ url: 'pages/DoorLockPage' })
      }
    })
  }

  @Builder
  NavItem(label: string, active: boolean, handler?: () => void) {
    Column() {
      Text(label)
        .fontSize(12)
        .fontColor(active ? '#1A3C6E' : '#999')
        .fontWeight(active ? FontWeight.Bold : FontWeight.Normal)
    }
    .layoutWeight(1)
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .onClick(() => {
      if (handler) handler()
    })
  }
}
