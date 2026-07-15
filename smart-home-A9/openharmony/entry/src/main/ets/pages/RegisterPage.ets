import { register } from '../common/ApiClient'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { StatusBanner } from '../common/ControlCenterKit'
import { UiText } from '../common/UiText'

function localizeMessage(message: string, fallback: string): string {
  if (!message) {
    return fallback
  }
  let transportMessage = UiText.mapTransportMessage(message)
  return transportMessage !== message ? transportMessage : message
}

@Entry
@Component
struct RegisterPage {
  @State user: string = ''
  @State pwd: string = ''
  @State pwd2: string = ''
  @State loading: boolean = false
  @State err: string = ''

  build() {
    Scroll() {
      Column() {
        Column() {
          Text('家')
            .width(46)
            .height(46)
            .borderRadius(14)
            .backgroundColor(ControlCenterTheme.loginAccent)
            .fontSize(25)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
            .textAlign(TextAlign.Center)
            .padding({ top: 7 })
          Text('创建你的智居账号')
            .fontSize(26)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
            .margin({ top: 24 })
          Text('注册后即可管理设备、场景和自动化规则。')
            .fontSize(13)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 10 })
        }
        .width('100%')
        .padding({ left: 24, right: 24, top: 28, bottom: 30 })
        .borderRadius(ControlCenterTheme.radiusCard)
        .backgroundColor(ControlCenterTheme.loginHeroBg)
        .alignItems(HorizontalAlign.Start)

        Column() {
          Text('创建账号')
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('使用至少 6 位密码保护你的家庭控制权限。')
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 6 })

          TextInput({ placeholder: '请输入用户名', text: this.user })
            .height(ControlCenterTheme.controlHeight)
            .width('100%')
            .borderRadius(ControlCenterTheme.radiusInner)
            .backgroundColor(ControlCenterTheme.loginFieldBg)
            .fontSize(16)
            .padding({ left: 14, right: 14 })
            .margin({ top: 20 })
            .onChange((value: string) => { this.user = value })

          TextInput({ placeholder: '请输入密码（至少 6 位）', text: this.pwd })
            .type(InputType.Password)
            .height(ControlCenterTheme.controlHeight)
            .width('100%')
            .borderRadius(ControlCenterTheme.radiusInner)
            .backgroundColor(ControlCenterTheme.loginFieldBg)
            .fontSize(16)
            .padding({ left: 14, right: 14 })
            .margin({ top: 12 })
            .onChange((value: string) => { this.pwd = value })

          TextInput({ placeholder: '请再次输入密码', text: this.pwd2 })
            .type(InputType.Password)
            .height(ControlCenterTheme.controlHeight)
            .width('100%')
            .borderRadius(ControlCenterTheme.radiusInner)
            .backgroundColor(ControlCenterTheme.loginFieldBg)
            .fontSize(16)
            .padding({ left: 14, right: 14 })
            .margin({ top: 12 })
            .onChange((value: string) => { this.pwd2 = value })

          if (this.err) {
            StatusBanner({ message: this.err, detail: '请检查输入后再试一次', tone: 'danger' })
              .margin({ top: 14 })
          }

          Button(this.loading ? '注册中...' : '创建账号')
            .type(ButtonType.Capsule)
            .width('100%')
            .height(52)
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .backgroundColor(ControlCenterTheme.loginAccent)
            .fontColor('#FFFFFF')
            .borderRadius(ControlCenterTheme.radiusInner)
            .enabled(!this.loading)
            .margin({ top: 18 })
            .onClick(() => this.doRegister())

          Row() {
            Text('已有账号？')
              .fontSize(13)
              .fontColor(ControlCenterTheme.textSecondary)
            Text(' 立即登录')
              .fontSize(13)
              .fontWeight(FontWeight.Bold)
              .fontColor(ControlCenterTheme.loginAccent)
              .onClick(() => this.getUIContext().getRouter().back())
          }
          .margin({ top: 18 })
        }
        .width('100%')
        .padding({ left: 20, right: 20, top: 22, bottom: 24 })
        .borderRadius(ControlCenterTheme.radiusCard)
        .backgroundColor(ControlCenterTheme.surface)
        .border({ width: 1, color: ControlCenterTheme.border })
        .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
        .margin({ top: 16 })
      }
      .width('100%')
      .padding({ left: 18, right: 18, top: 24, bottom: 30 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(ControlCenterTheme.loginPageBg)
    .scrollBar(BarState.Off)
  }

  async doRegister(): Promise<void> {
    if (!this.user || !this.pwd || !this.pwd2) {
      this.err = '请填写所有字段'
      return
    }
    if (this.pwd.length < 6) {
      this.err = '密码至少需要 6 位'
      return
    }
    if (this.pwd !== this.pwd2) {
      this.err = '两次输入的密码不一致'
      return
    }
    this.loading = true
    this.err = ''
    try {
      await register(this.user, this.pwd)
      this.getUIContext().getRouter().replaceUrl({ url: 'pages/DashboardPage' })
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '注册失败')
    } finally {
      this.loading = false
    }
  }
}
