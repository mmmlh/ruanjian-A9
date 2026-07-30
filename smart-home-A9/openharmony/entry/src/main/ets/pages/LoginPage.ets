import { getToken, initApiClient, login } from '../common/ApiClient'
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
struct LoginPage {
  @State user: string = ''
  @State pwd: string = ''
  @State loading: boolean = false
  @State err: string = ''

  aboutToAppear(): void {
    initApiClient().then(() => {
      if (getToken()) {
        this.getUIContext().getRouter().replaceUrl({ url: 'pages/DashboardPage' })
      }
    })
  }

  build() {
    Scroll() {
      Column() {
        this.buildHero()
        this.buildFormCard()
      }
      .width('100%')
      .padding({ left: 18, right: 18, top: 24, bottom: 30 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor(ControlCenterTheme.pageBg)
    .scrollBar(BarState.Off)
  }

  @Builder buildHero() {
    Column() {
      Row() {
        Text('家')
          .width(46)
          .height(46)
          .borderRadius(ControlCenterTheme.radiusInner)
          .backgroundColor(ControlCenterTheme.accent)
          .fontSize(25)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.surface)
          .textAlign(TextAlign.Center)
          .padding({ top: 7 })

        Text('智居')
          .fontSize(25)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
          .margin({ left: 12 })
      }
      .width('100%')
      .alignItems(VerticalAlign.Center)

      Text('连接家的每一刻')
        .fontSize(26)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ top: 26 })

      Text('让全屋设备，简单地协同工作')
        .fontSize(13)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: 10 })
    }
    .width('100%')
    .padding({ left: 24, right: 24, top: 28, bottom: 30 })
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(ControlCenterTheme.surfaceMuted)
  }

  @Builder buildFormCard() {
    Column() {
      Row() {
        Column() {
          Text('欢迎登录')
            .fontSize(22)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('登录后即可查看设备、场景与实时状态。')
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 6 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Start)

        Text('安全连接')
          .fontSize(12)
          .fontColor(ControlCenterTheme.accent)
          .padding({ left: 10, right: 10, top: 6, bottom: 6 })
          .borderRadius(ControlCenterTheme.radiusPill)
          .backgroundColor(ControlCenterTheme.accentSoft)
      }
      .width('100%')

      Text('用户名')
        .width('100%')
        .fontSize(12)
        .fontWeight(FontWeight.Medium)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ top: 20, bottom: 6 })

      TextInput({ placeholder: '请输入用户名', text: this.user })
        .type(InputType.Normal)
        .height(ControlCenterTheme.controlHeight)
        .width('100%')
        .borderRadius(ControlCenterTheme.radiusInner)
        .backgroundColor(ControlCenterTheme.surfaceMuted)
        .fontSize(16)
        .padding({ left: 14, right: 14 })
        .onChange((value: string) => { this.user = value })

      Text('密码')
        .width('100%')
        .fontSize(12)
        .fontWeight(FontWeight.Medium)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ top: 12, bottom: 6 })

      TextInput({ placeholder: '请输入密码', text: this.pwd })
        .type(InputType.Password)
        .height(ControlCenterTheme.controlHeight)
        .width('100%')
        .borderRadius(ControlCenterTheme.radiusInner)
        .backgroundColor(ControlCenterTheme.surfaceMuted)
        .fontSize(16)
        .padding({ left: 14, right: 14 })
        .onChange((value: string) => { this.pwd = value })

      if (this.err) {
        StatusBanner({
          message: this.err,
          detail: '请检查账号、密码或网络连接',
          tone: 'danger'
        }).margin({ top: 14 })
      }

      Button(this.loading ? '登录中...' : '登录')
        .type(ButtonType.Capsule)
        .width('100%')
        .height(ControlCenterTheme.controlHeight)
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .backgroundColor(ControlCenterTheme.accent)
        .fontColor(ControlCenterTheme.surface)
        .borderRadius(ControlCenterTheme.radiusInner)
        .enabled(!this.loading)
        .margin({ top: 18 })
        .onClick(() => this.doLogin())

      Row() {
        Text('还没有账号？')
          .fontSize(13)
          .fontColor(ControlCenterTheme.textSecondary)
        Button('立即注册')
          .height(ControlCenterTheme.tapTarget)
          .padding({ left: ControlCenterTheme.spaceSm, right: ControlCenterTheme.spaceSm })
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.accent)
          .backgroundColor(Color.Transparent)
          .onClick(() => {
            this.getUIContext().getRouter().pushUrl({ url: 'pages/RegisterPage' })
          })
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

  async doLogin(): Promise<void> {
    if (!this.user || !this.pwd) {
      this.err = '请输入用户名和密码'
      return
    }
    this.loading = true
    this.err = ''
    try {
      await login(this.user, this.pwd)
      this.getUIContext().getRouter().replaceUrl({ url: 'pages/DashboardPage' })
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '登录失败')
    } finally {
      this.loading = false
    }
  }
}
