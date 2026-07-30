import { getMe, changePassword, logout } from '../common/ApiClient'
import { UiText } from '../common/UiText'
import { UserInfo } from '../model/DeviceModel'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { AppBottomNav, StatusBanner } from '../common/ControlCenterKit'

const PAGE_BG: string = ControlCenterTheme.pageBg
const HERO_BG: string = ControlCenterTheme.surface
const CARD_BG: string = ControlCenterTheme.surface
const PRIMARY: string = ControlCenterTheme.accent
const DANGER: string = ControlCenterTheme.danger
const TEXT_PRIMARY: string = ControlCenterTheme.textPrimary
const TEXT_SECONDARY: string = ControlCenterTheme.textSecondary

function localizeMessage(message: string, fallback: string): string {
  if (!message) {
    return fallback
  }
  let transportMessage = UiText.mapTransportMessage(message)
  return transportMessage !== message ? transportMessage : message
}

@Entry
@Component
struct ProfilePage {
  @State user: UserInfo = new UserInfo()
  @State loading: boolean = true
  @State showPwd: boolean = false
  @State old: string = ''
  @State np: string = ''
  @State np2: string = ''
  @State pageErr: string = ''
  @State pageOk: string = ''
  @State pwdErr: string = ''
  @State changing: boolean = false
  @State showLogoutConfirm: boolean = false

  aboutToAppear(): void {
    this.ld()
  }

  async ld(): Promise<void> {
    this.loading = true
    this.pageErr = ''
    try {
      this.user = await getMe()
    } catch (err) {
      this.pageErr = localizeMessage((err as Error).message, '加载个人信息失败')
    } finally {
      this.loading = false
    }
  }

  async doPwd(): Promise<void> {
    this.pwdErr = ''
    if (!this.old || !this.np || !this.np2) {
      this.pwdErr = '请填写所有字段'
      return
    }
    if (this.np.length < 6) {
      this.pwdErr = '新密码至少需要 6 位'
      return
    }
    if (this.np !== this.np2) {
      this.pwdErr = '两次输入的密码不一致'
      return
    }
    this.changing = true
    try {
      await changePassword(this.old, this.np)
      this.pageOk = '密码修改成功'
      this.old = ''
      this.np = ''
      this.np2 = ''
      this.showPwd = false
    } catch (err) {
      this.pwdErr = localizeMessage((err as Error).message, '密码修改失败')
    } finally {
      this.changing = false
    }
  }

  async doOut(): Promise<void> {
    this.pageErr = ''
    this.pageOk = ''
    try {
      await logout()
      this.getUIContext().getRouter().replaceUrl({ url: 'pages/LoginPage' })
    } catch (err) {
      this.pageErr = localizeMessage((err as Error).message, '退出登录失败')
    }
  }

  rt(role: string): string {
    if (role === 'admin') return '管理员'
    return '家庭成员'
  }

  build() {
    Stack() {
      Column() {
        if (this.loading) {
          this.buildLoading()
        } else {
          Scroll() {
            Column() {
              this.buildTopBar()
              if (this.pageErr) {
                this.buildGlobalError(this.pageErr)
              }
              if (this.pageOk) {
                this.buildGlobalSuccess(this.pageOk)
              }
              this.buildHero()
              this.buildSecurityCard()
              this.buildSessionCard()
            }
            .padding({ left: 16, right: 16, top: 16, bottom: 24 })
            .constraintSize({ minHeight: '100%' })
          }
          .layoutWeight(1)
          .scrollBar(BarState.Off)
        }
        if (!this.showLogoutConfirm) {
          AppBottomNav({ active: 'profile' })
        }
      }
      .width('100%')
      .height('100%')

      if (this.showLogoutConfirm) {
        this.buildLogoutConfirm()
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(PAGE_BG)
  }

  @Builder buildTopBar() {
    Column() {
      Text('我的')
        .fontSize(ControlCenterTheme.pageTitleSize)
        .fontWeight(FontWeight.Bold)
        .fontColor(TEXT_PRIMARY)
      Text('账户、安全与会话管理')
        .fontSize(ControlCenterTheme.assistSize)
        .fontColor(TEXT_SECONDARY)
        .margin({ top: 4 })
    }
    .width('100%')
    .alignItems(HorizontalAlign.Start)
  }

  @Builder buildGlobalError(message: string) {
    StatusBanner({ message: message, detail: '请稍后重试', tone: 'danger' })
      .margin({ top: 14 })
  }

  @Builder buildGlobalSuccess(message: string) {
    StatusBanner({ message: message, tone: 'success' })
      .margin({ top: 14 })
  }

  @Builder buildHero() {
    Row() {
      Column() {
        Text('\uD83D\uDC64').fontSize(34)
      }
      .width(56)
      .height(56)
      .borderRadius(28)
      .backgroundColor(ControlCenterTheme.surfaceMuted)
      .justifyContent(FlexAlign.Center)
      .alignItems(HorizontalAlign.Center)

      Column() {
        Text(this.user.username || '智能家居用户')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor(TEXT_PRIMARY)
        Text(this.rt(this.user.role) + ' · 用户 ' + this.user.id.toString())
          .fontSize(ControlCenterTheme.assistSize)
          .fontColor(TEXT_SECONDARY)
          .margin({ top: 5 })
      }
      .layoutWeight(1)
      .margin({ left: 14 })
      .alignItems(HorizontalAlign.Start)
    }
    .width('100%')
    .padding(18)
    .borderRadius(ControlCenterTheme.radiusHero)
    .backgroundColor(HERO_BG)
    .border({ width: 1, color: ControlCenterTheme.border })
    .shadow({ radius: 10, color: ControlCenterTheme.shadowSoft, offsetY: 4 })
    .margin({ top: 16 })
    .alignItems(VerticalAlign.Center)
  }

  @Builder buildAccountCard() {
    Column() {
      this.cardTitle('账户信息', '基础身份与角色信息')
      this.infoRow('用户名', this.user.username)
      this.infoRow('角色', this.rt(this.user.role))
      this.infoRow('用户编号', this.user.id.toString())
    }
    .width('100%')
    .padding(16)
    .borderRadius(22)
    .backgroundColor(CARD_BG)
    .margin({ top: 16 })
  }

  @Builder buildSecurityCard() {
    Column() {
      Row() {
        this.cardTitle('安全设置', '更新您的账户密码')
        Blank()
        Button(this.showPwd ? '收起' : '修改密码')
          .type(ButtonType.Capsule)
          .height(ControlCenterTheme.tapTarget)
          .fontSize(ControlCenterTheme.assistSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(PRIMARY)
          .backgroundColor(ControlCenterTheme.accentSoft)
          .onClick(() => {
            this.showPwd = !this.showPwd
            this.pwdErr = ''
          })
      }
      .width('100%')

      if (this.showPwd) {
        TextInput({ placeholder: '请输入当前密码', text: this.old })
          .type(InputType.Password)
          .height(46)
          .width('100%')
          .borderRadius(14)
          .backgroundColor('#F4F7FA')
          .fontSize(14)
          .padding({ left: 14 })
          .margin({ top: 14 })
          .onChange((v: string) => { this.old = v })

        TextInput({ placeholder: '请输入新密码', text: this.np })
          .type(InputType.Password)
          .height(46)
          .width('100%')
          .borderRadius(14)
          .backgroundColor('#F4F7FA')
          .fontSize(14)
          .padding({ left: 14 })
          .margin({ top: 10 })
          .onChange((v: string) => { this.np = v })

        TextInput({ placeholder: '请确认新密码', text: this.np2 })
          .type(InputType.Password)
          .height(46)
          .width('100%')
          .borderRadius(14)
          .backgroundColor('#F4F7FA')
          .fontSize(14)
          .padding({ left: 14 })
          .margin({ top: 10 })
          .onChange((v: string) => { this.np2 = v })

        if (this.pwdErr) {
          Text(this.pwdErr).fontSize(12).fontColor('#A04444').margin({ top: 10 }).width('100%')
        }
        Button(this.changing ? '更新中...' : '确认修改密码')
          .type(ButtonType.Capsule)
          .width('100%')
          .height(46)
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .backgroundColor(PRIMARY)
          .borderRadius(14)
          .enabled(!this.changing)
          .margin({ top: 14 })
          .onClick(() => this.doPwd())
      }
    }
    .width('100%')
    .padding(16)
    .borderRadius(22)
    .backgroundColor(CARD_BG)
    .margin({ top: 16 })
  }

  @Builder buildSessionCard() {
    Column() {
      this.cardTitle('会话管理', '管理当前登录会话')

      Button('退出登录')
        .type(ButtonType.Capsule)
        .width('100%')
        .height(ControlCenterTheme.tapTarget)
        .fontSize(ControlCenterTheme.bodySize)
        .fontWeight(FontWeight.Bold)
        .fontColor(DANGER)
        .backgroundColor(ControlCenterTheme.dangerSoft)
        .borderRadius(14)
        .margin({ top: 14 })
        .onClick(() => { this.showLogoutConfirm = true })
    }
    .width('100%')
    .padding(16)
    .borderRadius(22)
    .backgroundColor(CARD_BG)
    .margin({ top: 16 })
  }

  @Builder cardTitle(title: string, subtitle: string) {
    Column() {
      Text(title).fontSize(16).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY)
      Text(subtitle).fontSize(ControlCenterTheme.assistSize).fontColor(TEXT_SECONDARY).margin({ top: 5 })
    }
    .alignItems(HorizontalAlign.Start)
  }

  @Builder infoRow(label: string, value: string) {
    Row() {
      Text(label).fontSize(13).fontColor(TEXT_SECONDARY)
      Blank()
      Text(value || '--').fontSize(13).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY)
    }
    .width('100%')
    .padding({ top: 14, bottom: 14 })
    .border({ width: { bottom: 0.5 }, color: '#EDF1F5' })
  }

  @Builder buildLogoutConfirm() {
    Column() {
      Column() {
        Text('退出登录')
          .fontSize(ControlCenterTheme.sectionTitleSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(TEXT_PRIMARY)
        Text('确定退出“' + (this.user.username || '当前账号') + '”吗？下次使用需要重新登录。')
          .fontSize(ControlCenterTheme.bodySize)
          .fontColor(TEXT_SECONDARY)
          .margin({ top: 10 })
        Row() {
          Button('取消')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(ControlCenterTheme.bodySize)
            .fontColor(TEXT_PRIMARY)
            .backgroundColor(ControlCenterTheme.surfaceMuted)
            .borderRadius(ControlCenterTheme.radiusInner)
            .onClick(() => { this.showLogoutConfirm = false })
          Blank().width(10)
          Button('确认退出')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(ControlCenterTheme.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
            .backgroundColor(DANGER)
            .borderRadius(ControlCenterTheme.radiusInner)
            .onClick(() => {
              this.showLogoutConfirm = false
              this.doOut()
            })
        }
        .width('100%')
        .margin({ top: 18 })
      }
      .width('86%')
      .padding(20)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(CARD_BG)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(ControlCenterTheme.overlay)
  }

  @Builder buildLoading() {
    Column() {
      LoadingProgress().width(34).height(34).color(PRIMARY)
      Text('正在加载个人信息...').fontSize(13).fontColor(TEXT_SECONDARY).margin({ top: 14 })
    }
    .width('100%')
    .layoutWeight(1)
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }
}
