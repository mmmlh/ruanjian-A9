import { DEFAULT_SERVER_URL } from '../common/SecureStorage'
import { getBaseUrl, getToken, initApiClient, login, setBaseUrl } from '../common/ApiClient'
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
  @State url: string = DEFAULT_SERVER_URL
  @State showCfg: boolean = false

  aboutToAppear(): void {
    initApiClient().then(() => {
      this.url = getBaseUrl() || DEFAULT_SERVER_URL
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
    .backgroundColor(ControlCenterTheme.loginPageBg)
    .scrollBar(BarState.Off)
  }

  @Builder buildHero() {
    Column() {
      Row() {
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
    .backgroundColor(ControlCenterTheme.loginHeroBg)
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
          .fontSize(11)
          .fontColor(ControlCenterTheme.loginAccent)
          .padding({ left: 10, right: 10, top: 6, bottom: 6 })
          .borderRadius(ControlCenterTheme.radiusPill)
          .backgroundColor(ControlCenterTheme.loginAccentSoft)
      }
      .width('100%')

      TextInput({ placeholder: '请输入用户名', text: this.user })
        .type(InputType.Normal)
        .height(50)
        .width('100%')
        .borderRadius(16)
        .backgroundColor(ControlCenterTheme.loginFieldBg)
        .fontSize(16)
        .padding({ left: 14, right: 14 })
        .margin({ top: 20 })
        .onChange((value: string) => { this.user = value })

      TextInput({ placeholder: '请输入密码', text: this.pwd })
        .type(InputType.Password)
        .height(50)
        .width('100%')
        .borderRadius(16)
        .backgroundColor(ControlCenterTheme.loginFieldBg)
        .fontSize(16)
        .padding({ left: 14, right: 14 })
        .margin({ top: 12 })
        .onChange((value: string) => { this.pwd = value })

      Row() {
        Text(this.showCfg ? '收起服务器配置' : '展开服务器配置')
          .fontSize(12)
          .fontColor(ControlCenterTheme.textSecondary)
      }
      .margin({ top: 14 })
      .onClick(() => { this.showCfg = !this.showCfg })

      if (this.showCfg) {
        Column() {
          Text('服务器地址')
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .width('100%')
          TextInput({ placeholder: DEFAULT_SERVER_URL, text: this.url })
            .type(InputType.Normal)
            .height(46)
            .width('100%')
            .borderRadius(16)
            .backgroundColor(ControlCenterTheme.loginFieldBg)
            .fontSize(13)
            .padding({ left: 14, right: 14 })
            .margin({ top: 8 })
            .onChange((value: string) => { this.url = value })
          StatusBanner({
            message: '部署地址仍然保持可配置',
            detail: '不影响现有 API 初始化和存储逻辑',
            tone: 'info'
          }).margin({ top: 10 })
        }
        .width('100%')
        .margin({ top: 12 })
      }

      if (this.err) {
        StatusBanner({
          message: this.err,
          detail: '请检查账号、密码或服务地址',
          tone: 'danger'
        }).margin({ top: 14 })
      }

      Button(this.loading ? '登录中...' : '登录')
        .type(ButtonType.Capsule)
        .width('100%')
        .height(52)
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .backgroundColor(ControlCenterTheme.loginAccent)
        .fontColor('#FFFFFF')
        .borderRadius(18)
        .enabled(!this.loading)
        .margin({ top: 18 })
        .onClick(() => this.doLogin())

      Row() {
        Text('还没有账号？')
          .fontSize(13)
          .fontColor(ControlCenterTheme.textSecondary)
        Text(' 立即注册')
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.loginAccent)
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
      setBaseUrl(this.url)
      await login(this.user, this.pwd)
      this.getUIContext().getRouter().replaceUrl({ url: 'pages/DashboardPage' })
    } catch (err) {
      this.err = localizeMessage((err as Error).message, '登录失败')
    } finally {
      this.loading = false
    }
  }
}
