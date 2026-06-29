import { router } from '@kit.ArkUI'
import { getDevices, sendCommand } from '../common/ApiClient'
import { Device, DeviceStatus, parseDeviceStatus, CommandParams } from '../model/DeviceModel'

class ModeItem {
  label: string = ''
  value: string = ''
  icon: string = ''
}

class FanItem {
  label: string = ''
  value: string = ''
}

let MODES: ModeItem[] = [
  { label: '制冷', value: 'cool', icon: '\u2744\uFE0F' },
  { label: '制热', value: 'heat', icon: '\uD83D\uDD25' },
  { label: '除湿', value: 'dehumidify', icon: '\uD83D\uDCA7' },
  { label: '送风', value: 'fan_only', icon: '\uD83C\uDF00' },
  { label: '自动', value: 'auto', icon: '\uD83D\uDD04' },
]

let FANS: FanItem[] = [
  { label: '自动', value: 'auto' },
  { label: '低速', value: 'low' },
  { label: '中速', value: 'medium' },
  { label: '高速', value: 'high' },
]

@Entry
@Component
struct ACControlPage {
  @State acs: Device[] = []
  @State selectedAC: number = 0
  @State isOn: boolean = false
  @State temp: number = 26
  @State mode: string = 'cool'
  @State fan: string = 'auto'
  @State brand: string = 'gree'
  @State isLoading: boolean = false

  aboutToAppear() {
    this.loadACs()
  }

  async loadACs() {
    try {
      let devices = await getDevices(undefined, 'ac')
      this.acs = devices
      if (this.acs.length > 0) {
        this.parseStatus(this.acs[0])
      }
    } catch (err) {
      console.error('Load AC failed', err)
    }
  }

  parseStatus(device: Device) {
    let status = parseDeviceStatus(device.status_json)
    this.isOn = status.power === 'on'
    this.temp = status.temp || 26
    this.mode = status.mode || 'cool'
    this.fan = status.fan || 'auto'
    this.brand = status.brand || device.brand || 'gree'
  }

  async toggleAC() {
    this.isLoading = true
    try {
      let device = this.acs[this.selectedAC]
      if (this.isOn) {
        await sendCommand(device.id, 'off')
      } else {
        let params = new CommandParams()
        params.mode = this.mode
        params.temp = this.temp
        params.fan = this.fan
        await sendCommand(device.id, 'set', params)
      }
      this.isOn = !this.isOn
    } catch (err) {
      console.error('Toggle AC failed', err)
    } finally {
      this.isLoading = false
    }
  }

  async setTemp(delta: number) {
    let newTemp = Math.max(16, Math.min(30, this.temp + delta))
    this.temp = newTemp
    if (this.isOn) {
      let device = this.acs[this.selectedAC]
      let params = new CommandParams()
      params.temp = newTemp
      await sendCommand(device.id, 'set', params)
    }
  }

  async setMode(newMode: string) {
    this.mode = newMode
    if (this.isOn) {
      let device = this.acs[this.selectedAC]
      let params = new CommandParams()
      params.mode = newMode
      await sendCommand(device.id, 'set', params)
    }
  }

  async setFan(newFan: string) {
    this.fan = newFan
    if (this.isOn) {
      let device = this.acs[this.selectedAC]
      let params = new CommandParams()
      params.fan = newFan
      await sendCommand(device.id, 'set', params)
    }
  }

  getModeLabel(modeValue: string): string {
    for (let i = 0; i < MODES.length; i++) {
      if (MODES[i].value === modeValue) {
        return MODES[i].label
      }
    }
    return ''
  }

  build() {
    Column() {
      Row() {
        Text('<')
          .fontSize(24)
          .fontColor(Color.White)
          .padding(8)
          .onClick(() => router.back())
        Text('空调控制')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)
        Blank()
        Text(this.brand.toUpperCase())
          .fontSize(11)
          .fontColor(Color.White)
          .padding({ left: 8, right: 8, top: 4, bottom: 4 })
          .borderRadius(4)
          .backgroundColor('#FFFFFF30')
      }
      .width('100%')
      .height(56)
      .padding({ left: 16, right: 16 })
      .alignItems(VerticalAlign.Center)
      .linearGradient({
        direction: GradientDirection.Right,
        colors: [['#1A3C6E', 0.0], ['#2B579A', 1.0]]
      })

      Scroll() {
        Column() {
          Column() {
            Text(this.isOn ? '\uD83C\uDF21\uFE0F' : '\uD83D\uDD0C')
              .fontSize(40)
            Text(`${this.temp}°C`)
              .fontSize(56)
              .fontWeight(FontWeight.Bold)
              .fontColor(this.isOn ? '#1A3C6E' : '#CCC')
            Text(this.isOn ? this.getModeLabel(this.mode) : '已关闭')
              .fontSize(16)
              .fontColor('#666')
          }
          .width('100%')
          .padding(30)
          .alignItems(HorizontalAlign.Center)

          Row() {
            Button('-')
              .type(ButtonType.Circle)
              .width(56)
              .height(56)
              .fontSize(24)
              .backgroundColor('#E0E0E0')
              .fontColor('#333')
              .onClick(() => this.setTemp(-1))

            Blank().width(60)

            Button('+')
              .type(ButtonType.Circle)
              .width(56)
              .height(56)
              .fontSize(24)
              .backgroundColor('#E0E0E0')
              .fontColor('#333')
              .onClick(() => this.setTemp(1))
          }
          .width('100%')
          .justifyContent(FlexAlign.Center)
          .margin({ bottom: 30 })

          Button(this.isOn ? '关闭空调' : '开启空调')
            .type(ButtonType.Capsule)
            .width('80%')
            .height(48)
            .fontSize(16)
            .backgroundColor(this.isOn ? '#F44336' : '#1A3C6E')
            .onClick(() => this.toggleAC())
            .margin({ bottom: 30 })

          Column() {
            Text('运行模式')
              .fontSize(15)
              .fontColor('#333')
              .margin({ bottom: 12 })
              .width('100%')

            GridRow({ columns: 5, gutter: 8 }) {
              ForEach(MODES, (m: ModeItem) => {
                GridCol() {
                  Column() {
                    Text(m.icon).fontSize(20)
                    Text(m.label).fontSize(11).fontColor(this.mode === m.value ? '#1A3C6E' : '#666')
                  }
                  .width('100%')
                  .padding(8)
                  .borderRadius(8)
                  .backgroundColor(this.mode === m.value ? '#E8EEF5' : '#F5F5F5')
                  .alignItems(HorizontalAlign.Center)
                  .onClick(() => this.setMode(m.value))
                }
              })
            }
          }
          .padding(16)
          .borderRadius(12)
          .backgroundColor(Color.White)
          .shadow({ radius: 4, color: '#1A000000', offsetY: 2 })
          .margin({ bottom: 16 })

          Column() {
            Text('风速')
              .fontSize(15)
              .fontColor('#333')
              .margin({ bottom: 12 })
              .width('100%')

            Row() {
              ForEach(FANS, (f: FanItem) => {
                Text(f.label)
                  .fontSize(13)
                  .fontColor(this.fan === f.value ? Color.White : '#666')
                  .padding({ left: 16, right: 16, top: 8, bottom: 8 })
                  .borderRadius(20)
                  .backgroundColor(this.fan === f.value ? '#1A3C6E' : '#F0F0F0')
                  .onClick(() => this.setFan(f.value))
                  .margin({ right: 8 })
              })
            }
          }
          .padding(16)
          .borderRadius(12)
          .backgroundColor(Color.White)
          .shadow({ radius: 4, color: '#1A000000', offsetY: 2 })
        }
        .padding(16)
      }
      .layoutWeight(1)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
