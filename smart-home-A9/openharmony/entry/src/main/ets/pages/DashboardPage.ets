import { router } from '@kit.ArkUI'
import { getRooms, getDevices, sendCommand, getToken } from '../common/ApiClient'
import { connectWS, disconnectWS } from '../common/MqttClient'
import { Room, Device, DeviceStatus, parseDeviceStatus } from '../model/DeviceModel'

@Entry
@Component
struct DashboardPage {
  @State rooms: Room[] = []
  @State devices: Device[] = []
  @State currentRoom: number = 0
  @State wsConnected: boolean = false
  @State temperature: string = '--'
  @State humidity: string = '--'

  aboutToAppear() {
    this.loadData()
    connectWS(
      (msg: string) => { this.onWSMessage(msg) },
      (connected: boolean) => { this.wsConnected = connected }
    )
  }

  aboutToDisappear() {
    disconnectWS()
  }

  async loadData() {
    try {
      this.rooms = await getRooms()
      this.devices = await getDevices()
    } catch (err) {
      console.error('Load data failed', err)
    }
  }

  onWSMessage(msg: string) {
    try {
      let m: Record<string, Object> = JSON.parse(msg) as Record<string, Object>
      let msgType = m['type']
      if (msgType !== undefined && msgType !== null) {
        let typeStr = msgType as string
        if (typeStr === 'sensor_update') {
          let dataObj = m['data']
          if (dataObj !== undefined && dataObj !== null) {
            let data = dataObj as Record<string, number>
            let tempVal = data['temperature']
            if (tempVal !== undefined && tempVal !== null) {
              this.temperature = tempVal.toString()
            }
            let humVal = data['humidity']
            if (humVal !== undefined && humVal !== null) {
              this.humidity = humVal.toString()
            }
          }
        } else if (typeStr === 'mqtt') {
          let topicObj = m['topic']
          let payloadObj = m['payload']
          if (topicObj !== undefined && topicObj !== null && payloadObj !== undefined && payloadObj !== null) {
            this.handleMqttUpdate(topicObj as string, payloadObj as Record<string, Object>)
          }
        }
      }
    } catch (e) {
      console.error('WS message parse failed', e)
    }
  }

  handleMqttUpdate(topic: string, payload: Record<string, Object>) {
    let parts = topic.split('/')
    if (parts.length < 4) return
    let deviceType = parts[2]

    let newDevices: Device[] = []
    for (let i = 0; i < this.devices.length; i++) {
      let d = this.devices[i]
      if (d.mqtt_topic === `home/${parts[1]}/${deviceType}`) {
        let updated = new Device()
        updated.id = d.id
        updated.room_id = d.room_id
        updated.type = d.type
        updated.name = d.name
        updated.brand = d.brand
        updated.mqtt_topic = d.mqtt_topic
        updated.status_json = JSON.stringify(payload)
        updated.room_name = d.room_name
        newDevices.push(updated)
      } else {
        newDevices.push(d)
      }
    }
    this.devices = newDevices

    if (deviceType === 'temperature_sensor') {
      let val = payload['value']
      if (val !== undefined && val !== null) {
        this.temperature = (val as number).toString()
      }
    } else if (deviceType === 'humidity_sensor') {
      let val = payload['value']
      if (val !== undefined && val !== null) {
        this.humidity = (val as number).toString()
      }
    }
  }

  getDevicesByRoom(roomId: number): Device[] {
    if (roomId === 0) return this.devices
    let filtered: Device[] = []
    for (let i = 0; i < this.devices.length; i++) {
      if (this.devices[i].room_id === roomId) {
        filtered.push(this.devices[i])
      }
    }
    return filtered
  }

  getStatusText(device: Device): string {
    let status = parseDeviceStatus(device.status_json)
    switch (device.type) {
      case 'light':
        return status.power === 'on' ? `开启 · 亮度${status.brightness}%` : '关闭'
      case 'ac':
        return status.power === 'on' ? `${status.mode} · ${status.temp}°C` : '关闭'
      case 'door_lock':
        return status.locked ? '已锁定' : '已解锁'
      case 'temperature_sensor':
        return `${status.value}°C`
      case 'humidity_sensor':
        return `${status.value}%`
      case 'pir_sensor':
        return status.presence ? '有人' : '无人'
      default:
        return '--'
    }
  }

  getDeviceIcon(device: Device): string {
    switch (device.type) {
      case 'light': return '\uD83D\uDCA1'
      case 'ac': return '\u2744\uFE0F'
      case 'door_lock': return '\uD83D\uDD12'
      case 'temperature_sensor': return '\uD83C\uDF21\uFE0F'
      case 'humidity_sensor': return '\uD83D\uDCA7'
      case 'pir_sensor': return '\uD83D\uDEB6'
      default: return '\uD83D\uDCF1'
    }
  }

  build() {
    Column() {
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

      Row() {
        Scroll() {
          Row() {
            Column() {
              this.RoomTab(0, '全部')
            }
            .margin({ right: 8 })
            ForEach(this.rooms, (room: Room) => {
              Column() {
                this.RoomTab(room.id, room.name)
              }
              .margin({ right: 8 })
            })
          }
        }
        .scrollable(ScrollDirection.Horizontal)
        .width('100%')
      }
      .padding({ left: 16, right: 16, top: 12, bottom: 8 })

      Scroll() {
        Column() {
          if (this.temperature !== '--' || this.humidity !== '--') {
            Row() {
              Column() {
                this.SensorCard('温度', `${this.temperature}°C`, '#FF9800')
              }
              .margin({ right: 12 })
              Column() {
                this.SensorCard('湿度', `${this.humidity}%`, '#2196F3')
              }
            }
            .width('100%')
            .margin({ bottom: 12 })
          }

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
