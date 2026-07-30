import { getMe, changePassword, logout } from '../common/ApiClient'
import { UiText } from '../common/UiText'
import { UserInfo } from '../model/DeviceModel'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { AppTopBar, AppBottomNav, ConfirmPanel } from '../common/ControlCenterKit'

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
  @State loading: boolean = false
  @State showPwd: boolean = false
  @State old: string = ''
  @State np: string = ''
  @State np2: string = ''
  @State pageErr: string = ''
  @State pageOk: string = ''
  @State pwdErr: string = ''
  @State changing: boolean = false
  @State confirmLogout: boolean = false
  @State loggingOut: boolean = false

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
    if (this.loggingOut) {
      return
    }
    this.loggingOut = true
    this.confirmLogout = false
    this.pageErr = ''
    this.pageOk = ''
    try {
      await logout()
      this.getUIContext().getRouter().replaceUrl({ url: 'pages/LoginPage' })
    } catch (err) {
      this.pageErr = localizeMessage((err as Error).message, '退出登录失败')
    } finally {
      this.loggingOut = false
    }
  }

  rt(role: string): string {
    if (role === 'admin') return '管理员'
    return '家庭成员'
  }

  build() {
    Stack() {
      Column() {
        AppTopBar({ title: '我的' })
          .padding({ left: ControlCenterTheme.gutter, right: ControlCenterTheme.gutter,
            top: ControlCenterTheme.spaceMd, bottom: ControlCenterTheme.spaceSm })

        if (this.pageErr || this.pageOk) {
          Column() {
            if (this.pageErr) {
              this.buildGlobalError(this.pageErr)
            }
            if (this.pageOk) {
              this.buildGlobalSuccess(this.pageOk)
            }
          }
          .width('100%')
          .padding({ left: ControlCenterTheme.gutter, right: ControlCenterTheme.gutter })
        }

        if (this.loading) {
          this.buildLoading()
        } else {
          Scroll() {
            Column() {
              this.buildHero()
              this.buildAccountCard()
              this.buildSecurityCard()
              this.buildSessionCard()
            }
            .padding({ left: 16, right: 16, top: 16, bottom: 24 })
          }
          .layoutWeight(1)
          .scrollBar(BarState.Off)
        }
        AppBottomNav({ active: 'profile' })
      }
      .width('100%')
      .height('100%')

      if (this.confirmLogout) {
        Column() {
          ConfirmPanel({
            title: '退出登录？',
            detail: '退出后需要重新登录才能继续管理家庭设备。',
            confirmLabel: '确认退出',
            cancelLabel: '取消',
            onCancel: () => { this.confirmLogout = false },
            onConfirm: () => this.doOut()
          })
        }
        .width('100%')
        .height('100%')
        .padding(ControlCenterTheme.gutter)
        .justifyContent(FlexAlign.Center)
        .alignItems(HorizontalAlign.Center)
        .backgroundColor(ControlCenterTheme.overlay)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(PAGE_BG)
  }

  @Builder buildGlobalError(message: string) {
    Text(message)
      .fontSize(13)
      .fontColor('#A04444')
      .padding({ left: 14, right: 14, top: 10, bottom: 10 })
      .borderRadius(14)
      .backgroundColor('#FBE3E3')
      .width('100%')
      .margin({ top: 14 })
  }

  @Builder buildGlobalSuccess(message: string) {
    Text(message)
      .fontSize(13)
      .fontColor('#1B8267')
      .padding({ left: 14, right: 14, top: 10, bottom: 10 })
      .borderRadius(14)
      .backgroundColor(ControlCenterTheme.accentSoft)
      .width('100%')
      .margin({ top: 14 })
  }

  @Builder buildHero() {
    Column() {
      Column() {
        Text('我').fontSize(28).fontWeight(FontWeight.Bold).fontColor(PRIMARY)
      }
      .width(72)
      .height(72)
      .borderRadius(36)
      .backgroundColor(ControlCenterTheme.accentSoft)
      .justifyContent(FlexAlign.Center)
      .alignItems(HorizontalAlign.Center)

      Text(this.user.username || '智能家居用户').fontSize(22).fontWeight(FontWeight.Bold).fontColor(TEXT_PRIMARY).margin({ top: 14 })
      Text(this.rt(this.user.role)).fontSize(13).fontColor(TEXT_SECONDARY).margin({ top: 6 })
    }
    .width('100%')
    .padding({ top: 24, bottom: 24 })
    .borderRadius(ControlCenterTheme.radiusHero)
    .backgroundColor(HERO_BG)
    .border({ width: 1, color: ControlCenterTheme.border })
    .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
    .margin({ top: 16 })
    .alignItems(HorizontalAlign.Center)
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
        Text(this.showPwd ? '隐藏' : '修改密码')
          .fontSize(12)
          .fontWeight(FontWeight.Bold)
          .fontColor(PRIMARY)
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

      Button(this.loggingOut ? '退出中...' : '退出登录')
        .type(ButtonType.Capsule)
        .width('100%')
        .height(ControlCenterTheme.tapTarget)
        .fontSize(14)
        .fontWeight(FontWeight.Bold)
        .backgroundColor(DANGER)
        .borderRadius(14)
        .enabled(!this.loggingOut)
        .margin({ top: 14 })
        .onClick(() => { this.confirmLogout = true })
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
      Text(subtitle).fontSize(11).fontColor(TEXT_SECONDARY).margin({ top: 5 })
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
