import { router } from '@kit.ArkUI'
import { getDevices, sendCommand, getAesKey } from '../common/ApiClient'
import { generateAuthCode } from '../common/CryptoUtil'
import { Device, DeviceStatus, parseDeviceStatus, CommandParams } from '../model/DeviceModel'

@Entry
@Component
struct DoorLockPage {
  @State locks: Device[] = []
  @State selectedLock: number = 0
  @State isLocked: boolean = true
  @State isLoading: boolean = false
  @State lastAction: string = ''
  @State autoLockCountdown: number = 0
  private autoLockTimer: number = -1

  aboutToAppear() {
    this.loadLocks()
  }

  aboutToDisappear() {
    this.clearAutoLockTimer()
  }

  clearAutoLockTimer() {
    if (this.autoLockTimer > 0) {
      clearTimeout(this.autoLockTimer)
      this.autoLockTimer = -1
    }
    this.autoLockCountdown = 0
  }

  startAutoLockTimer() {
    this.clearAutoLockTimer()
    this.autoLockCountdown = 5
    let tick = () => {
      this.autoLockCountdown--
      if (this.autoLockCountdown <= 0) {
        this.autoLockCountdown = 0
        this.toggleLock()
        return
      }
      if (this.isLocked) {
        this.clearAutoLockTimer()
        return
      }
      this.autoLockTimer = setTimeout(tick, 1000)
    }
    this.autoLockTimer = setTimeout(tick, 1000)
  }

  async loadLocks() {
    try {
      let devices = await getDevices(undefined, 'door_lock')
      this.locks = devices
      if (this.locks.length > 0) {
        this.parseStatus(this.locks[0])
      }
    } catch (err) {
      console.error('Load locks failed', err)
    }
  }

  parseStatus(device: Device) {
    let status = parseDeviceStatus(device.status_json)
    this.isLocked = status.locked
  }

  async toggleLock() {
    this.isLoading = true
    try {
      let device = this.locks[this.selectedLock]
      if (this.isLocked) {
        let aesKey = getAesKey()
        let encryptedAuth = await generateAuthCode(aesKey)
        let params = new CommandParams()
        params.auth_code = encryptedAuth
        await sendCommand(device.id, 'unlock', params)
        this.lastAction = '开锁成功 (已加密)'
      } else {
        this.clearAutoLockTimer()
        await sendCommand(device.id, 'lock')
        this.lastAction = '上锁成功'
      }
      this.isLocked = !this.isLocked
      if (!this.isLocked) {
        this.startAutoLockTimer()
      }
    } catch (err) {
      this.lastAction = '操作失败: ' + (err as Error).message
    } finally {
      this.isLoading = false
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
        Text('智能门禁')
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

      Column() {
        Column() {
          Text(this.isLocked ? '\uD83D\uDD12' : '\uD83D\uDD13')
            .fontSize(80)
          Text(this.isLocked ? '已锁定' : '已解锁')
            .fontSize(24)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.isLocked ? '#4CAF50' : '#FF9800')
            .margin({ top: 16 })
        }
        .width(200)
        .height(200)
        .borderRadius(100)
        .backgroundColor(this.isLocked ? '#E8F5E9' : '#FFF3E0')
        .border({ width: 4, color: this.isLocked ? '#4CAF50' : '#FF9800' })
        .alignItems(HorizontalAlign.Center)
        .justifyContent(FlexAlign.Center)
        .margin({ top: 60, bottom: 40 })

        Button(this.isLoading ? '处理中...' : (this.isLocked ? '\uD83D\uDD13 开 锁' : '\uD83D\uDD12 上 锁'))
          .type(ButtonType.Capsule)
          .width('70%')
          .height(56)
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .backgroundColor(this.isLocked ? '#4CAF50' : '#FF9800')
          .enabled(!this.isLoading)
          .onClick(() => this.toggleLock())

        if (this.lastAction) {
          Text(this.lastAction)
            .fontSize(14)
            .fontColor('#666')
            .margin({ top: 20 })
        }

        Row() {
          Text('\u26A0\uFE0F')
            .fontSize(14)
          Text('门禁操作已加密传输（AES-256 + JWT）')
            .fontSize(12)
            .fontColor('#999')
        }
        .margin({ top: 40 })

        if (!this.isLocked && this.autoLockCountdown > 0) {
          Row() {
            Text(`\u23F1\uFE0F ${this.autoLockCountdown}秒后自动上锁`)
              .fontSize(13)
              .fontColor('#FF9800')
          }
          .margin({ top: 12 })
        }
      }
      .width('100%')
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Center)
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
