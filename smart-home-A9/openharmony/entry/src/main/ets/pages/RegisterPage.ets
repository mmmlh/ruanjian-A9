/**
 * 注册页
 */
import { router } from '@kit.ArkUI'
import { register } from '../common/ApiClient'

@Entry
@Component
struct RegisterPage {
  @State username: string = ''
  @State password: string = ''
  @State confirmPassword: string = ''
  @State isLoading: boolean = false
  @State errorMsg: string = ''

  build() {
    Column() {
      Row()
        .width('100%')
        .height(200)
        .linearGradient({
          direction: GradientDirection.Bottom,
          colors: [['#1A3C6E', 0.0], ['#2B579A', 1.0]]
        })

      Column() {
        Text('创建账号')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A3C6E')
          .margin({ bottom: 8 })

        Text('注册您的智能家居账号')
          .fontSize(14)
          .fontColor('#999')
          .margin({ bottom: 30 })

        TextInput({ placeholder: '请输入用户名', text: this.username })
          .type(InputType.Normal)
          .height(50)
          .width('100%')
          .borderRadius(8)
          .backgroundColor('#F5F5F5')
          .padding({ left: 16 })
          .margin({ bottom: 16 })
          .onChange((value: string) => { this.username = value })

        TextInput({ placeholder: '请输入密码（至少6位）', text: this.password })
          .type(InputType.Password)
          .height(50)
          .width('100%')
          .borderRadius(8)
          .backgroundColor('#F5F5F5')
          .padding({ left: 16 })
          .margin({ bottom: 16 })
          .onChange((value: string) => { this.password = value })

        TextInput({ placeholder: '再次输入密码', text: this.confirmPassword })
          .type(InputType.Password)
          .height(50)
          .width('100%')
          .borderRadius(8)
          .backgroundColor('#F5F5F5')
          .padding({ left: 16 })
          .margin({ bottom: 16 })
          .onChange((value: string) => { this.confirmPassword = value })

        if (this.errorMsg) {
          Text(this.errorMsg)
            .fontSize(13)
            .fontColor('#F44336')
            .margin({ bottom: 12 })
            .width('100%')
        }

        Button(this.isLoading ? '注册中...' : '注 册')
          .type(ButtonType.Capsule)
          .width('100%')
          .height(48)
          .fontSize(16)
          .backgroundColor('#1A3C6E')
          .enabled(!this.isLoading)
          .onClick(() => this.doRegister())

        Row() {
          Text('已有账号？')
            .fontSize(13)
            .fontColor('#999')
          Text('立即登录')
            .fontSize(13)
            .fontColor('#2B579A')
            .onClick(() => {
              router.back()
            })
        }
        .margin({ top: 16 })
      }
      .padding(30)
      .width('90%')
      .borderRadius(16)
      .backgroundColor(Color.White)
      .shadow({ radius: 12, color: '#1A000000', offsetY: 4 })
      .position({ x: '5%', y: 140 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }

  async doRegister() {
    if (!this.username || !this.password || !this.confirmPassword) {
      this.errorMsg = '请填写所有字段'
      return
    }
    if (this.password.length < 6) {
      this.errorMsg = '密码至少需要6位'
      return
    }
    if (this.password !== this.confirmPassword) {
      this.errorMsg = '两次输入的密码不一致'
      return
    }
    this.isLoading = true
    this.errorMsg = ''
    try {
      await register(this.username, this.password)
      router.replaceUrl({ url: 'pages/DashboardPage' })
    } catch (err) {
      this.errorMsg = (err as Error).message || '注册失败'
    } finally {
      this.isLoading = false
    }
  }
}
