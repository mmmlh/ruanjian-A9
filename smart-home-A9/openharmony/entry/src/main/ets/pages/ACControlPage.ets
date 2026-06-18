/**
 * 空调控制页 — 温度、模式、风速、品牌切换
 */
import { router } from '@kit.ArkUI'
import { getDevices, sendCommand } from '../common/ApiClient'
import { Device, DeviceStatus } from '../model/DeviceModel'

const MODES = [
  { label: '制冷', value: 'cool', icon: '❄️' },
  { label: '制热', value: 'heat', icon: '🔥' },
  { label: '除湿', value: 'dehumidify', icon: '💧' },
  { label: '送风', value: 'fan_only', icon: '🌀' },
  { label: '自动', value: 'auto', icon: '🔄' },
]

const FANS = [
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
      const devices = await getDevices(undefined, 'ac')
      this.acs = devices as Device[]
      if (this.acs.length > 0) {
        this.parseStatus(this.acs[0])
      }
    } catch (err) {
      console.error('加载空调设备失败', err)
    }
  }

  parseStatus(device: Device) {
    try {
      const status: DeviceStatus = JSON.parse(device.status_json || '{}')
      this.isOn = status.power === 'on'
      this.temp = status.temp || 26
      this.mode = status.mode || 'cool'
      this.fan = status.fan || 'auto'
      this.brand = status.brand || device.brand || 'gree'
    } catch {
      // ignore
    }
  }

  async toggleAC() {
    this.isLoading = true
    try {
      const device = this.acs[this.selectedAC]
      if (this.isOn) {
        await sendCommand(device.id, 'off')
      } else {
        await sendCommand(device.id, 'set', {
          power: 'on', mode: this.mode, temp: this.temp, fan: this.fan
        })
      }
      this.isOn = !this.isOn
    } catch (err) {
      console.error('操作失败', err)
    } finally {
      this.isLoading = false
    }
  }

  async setTemp(delta: number) {
    const newTemp = Math.max(16, Math.min(30, this.temp + delta))
    this.temp = newTemp
    if (this.isOn) {
      const device = this.acs[this.selectedAC]
      await sendCommand(device.id, 'set', { temp: newTemp })
    }
  }

  async setMode(newMode: string) {
    this.mode = newMode
    if (this.isOn) {
      const device = this.acs[this.selectedAC]
      await sendCommand(device.id, 'set', { mode: newMode })
    }
  }

  async setFan(newFan: string) {
    this.fan = newFan
    if (this.isOn) {
      const device = this.acs[this.selectedAC]
      await sendCommand(device.id, 'set', { fan: newFan })
    }
  }

  build() {
    Column() {
      // 顶部栏
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
        // 品牌标签
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
          // 温度显示
          Column() {
            Text(this.isOn ? '🌡️' : '🔌')
              .fontSize(40)
            Text(`${this.temp}°C`)
              .fontSize(56)
              .fontWeight(FontWeight.Bold)
              .fontColor(this.isOn ? '#1A3C6E' : '#CCC')
            Text(this.isOn ? MODES.find(m => m.value === this.mode)?.label || '' : '已关闭')
              .fontSize(16)
              .fontColor('#666')
          }
          .width('100%')
          .padding(30)
          .alignItems(HorizontalAlign.Center)

          // 温度加减按钮
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

          // 开关按钮
          Button(this.isOn ? '关闭空调' : '开启空调')
            .type(ButtonType.Capsule)
            .width('80%')
            .height(48)
            .fontSize(16)
            .backgroundColor(this.isOn ? '#F44336' : '#1A3C6E')
            .onClick(() => this.toggleAC())
            .margin({ bottom: 30 })

          // 模式选择
          Column() {
            Text('运行模式')
              .fontSize(15)
              .fontColor('#333')
              .margin({ bottom: 12 })
              .width('100%')

            GridRow({ columns: 5, gutter: 8 }) {
              ForEach(MODES, (m: { label: string; value: string; icon: string }) => {
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

          // 风速选择
          Column() {
            Text('风速')
              .fontSize(15)
              .fontColor('#333')
              .margin({ bottom: 12 })
              .width('100%')

            Row() {
              ForEach(FANS, (f: { label: string; value: string }) => {
                Text(f.label)
                  .fontSize(13)
                  .fontColor(this.fan === f.value ? Color.White : '#666')
                  .padding({ left: 16, right: 16, top: 8, bottom: 8 })
                  .borderRadius(20)
                  .backgroundColor(this.fan === f.value ? '#1A3C6E' : '#F0F0F0')
                  .onClick(() => this.setFan(f.value))
              })
            }
            .space(8)
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
