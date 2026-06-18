/**
 * 登录页
 */
import { router } from '@kit.ArkUI'
import { login } from '../common/ApiClient'

@Entry
@Component
struct LoginPage {
  @State username: string = ''
  @State password: string = ''
  @State isLoading: boolean = false
  @State errorMsg: string = ''

  build() {
    Column() {
      // 顶部装饰
      Row()
        .width('100%')
        .height(200)
        .linearGradient({
          direction: GradientDirection.Bottom,
          colors: [['#1A3C6E', 0.0], ['#2B579A', 1.0]]
        })

      // 登录卡片
      Column() {
        // 标题
        Text('智能家居控制系统')
          .fontSize(24)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A3C6E')
          .margin({ bottom: 8 })

        Text('基于 OpenHarmony')
          .fontSize(14)
          .fontColor('#999')
          .margin({ bottom: 30 })

        // 用户名
        TextInput({ placeholder: '请输入用户名', text: this.username })
          .type(InputType.Normal)
          .height(50)
          .width('100%')
          .borderRadius(8)
          .backgroundColor('#F5F5F5')
          .padding({ left: 16 })
          .margin({ bottom: 16 })
          .onChange((value: string) => { this.username = value })

        // 密码
        TextInput({ placeholder: '请输入密码', text: this.password })
          .type(InputType.Password)
          .height(50)
          .width('100%')
          .borderRadius(8)
          .backgroundColor('#F5F5F5')
          .padding({ left: 16 })
          .margin({ bottom: 16 })
          .onChange((value: string) => { this.password = value })

        // 错误提示
        if (this.errorMsg) {
          Text(this.errorMsg)
            .fontSize(13)
            .fontColor('#F44336')
            .margin({ bottom: 12 })
            .width('100%')
        }

        // 登录按钮
        Button(this.isLoading ? '登录中...' : '登 录')
          .type(ButtonType.Capsule)
          .width('100%')
          .height(48)
          .fontSize(16)
          .backgroundColor('#1A3C6E')
          .enabled(!this.isLoading)
          .onClick(() => this.doLogin())

        // 注册入口
        Row() {
          Text('没有账号？')
            .fontSize(13)
            .fontColor('#999')
          Text('立即注册')
            .fontSize(13)
            .fontColor('#2B579A')
            .onClick(() => {
              router.pushUrl({ url: 'pages/RegisterPage' })
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

  async doLogin() {
    if (!this.username || !this.password) {
      this.errorMsg = '请输入用户名和密码'
      return
    }
    this.isLoading = true
    this.errorMsg = ''
    try {
      const result = await login(this.username, this.password)
      // 跳转到仪表盘
      router.replaceUrl({ url: 'pages/DashboardPage' })
    } catch (err) {
      this.errorMsg = (err as Error).message || '登录失败'
    } finally {
      this.isLoading = false
    }
  }
}
