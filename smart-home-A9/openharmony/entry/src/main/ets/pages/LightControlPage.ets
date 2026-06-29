import { router } from '@kit.ArkUI'
import { getDevices, sendCommand } from '../common/ApiClient'
import { Device, DeviceStatus, parseDeviceStatus, CommandParams } from '../model/DeviceModel'

@Entry
@Component
struct LightControlPage {
  @State lights: Device[] = []
  @State selectedLight: number = 0
  @State isOn: boolean = false
  @State brightnessValue: number = 80
  @State colorMode: string = 'warm'
  @State isLoading: boolean = false
  private brightnessTimer: number = -1

  aboutToAppear() {
    this.loadLights()
  }

  aboutToDisappear() {
    if (this.brightnessTimer > 0) {
      clearTimeout(this.brightnessTimer)
    }
  }

  async loadLights() {
    try {
      let devices = await getDevices(undefined, 'light')
      this.lights = devices
      if (this.lights.length > 0) {
        this.parseStatus(this.lights[0])
      }
    } catch (err) {
      console.error('Load lights failed', err)
    }
  }

  parseStatus(device: Device) {
    let status = parseDeviceStatus(device.status_json)
    this.isOn = status.power === 'on'
    this.brightnessValue = status.brightness || 80
    this.colorMode = status.color || 'warm'
  }

  async toggleLight() {
    this.isLoading = true
    try {
      let device = this.lights[this.selectedLight]
      let action = this.isOn ? 'off' : 'on'
      if (this.isOn) {
        await sendCommand(device.id, action)
      } else {
        let params = new CommandParams()
        params.brightness = this.brightnessValue
        params.color = this.colorMode
        await sendCommand(device.id, action, params)
      }
      this.isOn = !this.isOn
    } catch (err) {
      console.error('Toggle light failed', err)
    } finally {
      this.isLoading = false
    }
  }

  setBrightness(value: number) {
    this.brightnessValue = Math.round(value)
    if (this.brightnessTimer > 0) {
      clearTimeout(this.brightnessTimer)
    }
    if (this.isOn) {
      let device = this.lights[this.selectedLight]
      let targetBrightness = this.brightnessValue
      this.brightnessTimer = setTimeout(() => {
        let params = new CommandParams()
        params.brightness = targetBrightness
        sendCommand(device.id, 'set', params)
      }, 300)
    }
  }

  async setColorMode(mode: string) {
    this.colorMode = mode
    if (this.isOn) {
      let device = this.lights[this.selectedLight]
      let params = new CommandParams()
      params.color = mode
      await sendCommand(device.id, 'set', params)
    }
  }

  build() {
    Column() {
      Row() {
        Text('<')
          .fontSize(24)
          .fontColor(Color.White)
          .padding(8)
          .onClick(() => router.back())
        Text('照明控制')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor(Color.White)
      }
      .width('100%')
      .height(56)
      .padding({ left: 16 })
      .alignItems(VerticalAlign.Center)
      .linearGradient({
        direction: GradientDirection.Right,
        colors: [['#1A3C6E', 0.0], ['#2B579A', 1.0]]
      })

      Scroll() {
        Column() {
          if (this.lights.length > 1) {
            Row() {
              ForEach(this.lights, (light: Device, index: number) => {
                Text(light.name)
                  .fontSize(14)
                  .fontColor(this.selectedLight === index ? '#1A3C6E' : '#666')
                  .padding({ left: 16, right: 16, top: 8, bottom: 8 })
                  .borderRadius(20)
                  .backgroundColor(this.selectedLight === index ? '#E8EEF5' : 'transparent')
                  .onClick(() => {
                    this.selectedLight = index
                    this.parseStatus(light)
                  })
              })
            }
            .margin({ bottom: 20 })
          }

          Column() {
            Text(this.isOn ? '\uD83D\uDCA1' : '\uD83D\uDD0C')
              .fontSize(60)
            Text(this.isOn ? '已开启' : '已关闭')
              .fontSize(18)
              .fontWeight(FontWeight.Medium)
              .fontColor(this.isOn ? '#FF9800' : '#999')
              .margin({ top: 12 })
          }
          .width(160)
          .height(160)
          .borderRadius(80)
          .backgroundColor(this.isOn ? '#FFF8E1' : '#F5F5F5')
          .border({ width: 3, color: this.isOn ? '#FF9800' : '#E0E0E0' })
          .alignItems(HorizontalAlign.Center)
          .justifyContent(FlexAlign.Center)
          .margin({ bottom: 30 })
          .onClick(() => this.toggleLight())

          Column() {
            Row() {
              Text('亮度')
                .fontSize(15)
                .fontColor('#333')
              Blank()
              Text(`${this.brightnessValue}%`)
                .fontSize(15)
                .fontColor('#1A3C6E')
                .fontWeight(FontWeight.Bold)
            }
            .width('100%')

            Slider({
              value: this.brightnessValue,
              min: 0,
              max: 100,
              step: 1,
              style: SliderStyle.OutSet
            })
              .width('100%')
              .blockColor('#1A3C6E')
              .trackColor('#E0E0E0')
              .selectedColor('#1A3C6E')
              .onChange((value: number) => this.setBrightness(value))
          }
          .padding(16)
          .borderRadius(12)
          .backgroundColor(Color.White)
          .shadow({ radius: 4, color: '#1A000000', offsetY: 2 })
          .margin({ bottom: 16 })

          Column() {
            Text('色温模式')
              .fontSize(15)
              .fontColor('#333')
              .margin({ bottom: 12 })
              .width('100%')

            Row() {
              Column() {
                this.ColorChip('暖光', 'warm')
              }
              .margin({ right: 12 })
              Column() {
                this.ColorChip('冷光', 'cool')
              }
              .margin({ right: 12 })
              Column() {
                this.ColorChip('自然', 'natural')
              }
            }
            .width('100%')
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

  @Builder
  ColorChip(label: string, mode: string) {
    Text(label)
      .fontSize(13)
      .fontColor(this.colorMode === mode ? Color.White : '#666')
      .padding({ left: 20, right: 20, top: 8, bottom: 8 })
      .borderRadius(20)
      .backgroundColor(this.colorMode === mode ? '#1A3C6E' : '#F0F0F0')
      .onClick(() => this.setColorMode(mode))
  }
}
