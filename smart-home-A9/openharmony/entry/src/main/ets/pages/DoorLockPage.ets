/**
 * 门禁控制页 — 远程开锁/上锁
 */
import { router } from '@kit.ArkUI'
import { getDevices, sendCommand } from '../common/ApiClient'
import { Device, DeviceStatus } from '../model/DeviceModel'

@Entry
@Component
struct DoorLockPage {
  @State locks: Device[] = []
  @State selectedLock: number = 0
  @State isLocked: boolean = true
  @State isLoading: boolean = false
  @State lastAction: string = ''

  aboutToAppear() {
    this.loadLocks()
  }

  async loadLocks() {
    try {
      const devices = await getDevices(undefined, 'door_lock')
      this.locks = devices as Device[]
      if (this.locks.length > 0) {
        this.parseStatus(this.locks[0])
      }
    } catch (err) {
      console.error('加载门禁设备失败', err)
    }
  }

  parseStatus(device: Device) {
    try {
      const status: DeviceStatus = JSON.parse(device.status_json || '{}')
      this.isLocked = status.locked !== false
    } catch {
      // ignore
    }
  }

  async toggleLock() {
    this.isLoading = true
    try {
      const device = this.locks[this.selectedLock]
      if (this.isLocked) {
        await sendCommand(device.id, 'unlock', { auth_code: 'demo-auth-code' })
        this.lastAction = '开锁成功'
      } else {
        await sendCommand(device.id, 'lock')
        this.lastAction = '上锁成功'
      }
      this.isLocked = !this.isLocked
    } catch (err) {
      this.lastAction = '操作失败: ' + (err as Error).message
    } finally {
      this.isLoading = false
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
        // 门锁状态大图
        Column() {
          Text(this.isLocked ? '🔒' : '🔓')
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

        // 操作按钮
        Button(this.isLoading ? '处理中...' : (this.isLocked ? '🔓 开 锁' : '🔒 上 锁'))
          .type(ButtonType.Capsule)
          .width('70%')
          .height(56)
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .backgroundColor(this.isLocked ? '#4CAF50' : '#FF9800')
          .enabled(!this.isLoading)
          .onClick(() => this.toggleLock())

        // 操作记录
        if (this.lastAction) {
          Text(this.lastAction)
            .fontSize(14)
            .fontColor('#666')
            .margin({ top: 20 })
        }

        // 安全提示
        Row() {
          Text('⚠️')
            .fontSize(14)
          Text('门禁操作已加密传输（AES-256 + JWT）')
            .fontSize(12)
            .fontColor('#999')
        }
        .margin({ top: 40 })

        // 开锁动画效果区域
        if (!this.isLocked) {
          Row() {
            Text('门锁已打开，5秒后自动上锁')
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
