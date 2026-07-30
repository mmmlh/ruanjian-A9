@Entry(new LocalStorage())
@Component
struct WidgetCard {
  @LocalStorageProp('temperature') temperature: string = '--'
  @LocalStorageProp('humidity') humidity: string = '--'
  @LocalStorageProp('lightOn') lightOn: boolean = false
  @LocalStorageProp('acOn') acOn: boolean = false
  @LocalStorageProp('locked') locked: boolean = true
  @LocalStorageProp('curtainOpen') curtainOpen: boolean = false
  @LocalStorageProp('humidifierOn') humidifierOn: boolean = false
  @LocalStorageProp('updateTime') updateTime: string = '--:--'

  build() {
    Column() {
      Row() {
        Text('智能家居')
          .fontSize(14)
          .fontWeight(FontWeight.Bold)
          .fontColor('#1A3C6E')
        Blank()
        Text(this.updateTime)
          .fontSize(12)
          .fontColor('#777777')
          .margin({ right: 4 })
        Text('\uD83D\uDD04')
          .fontSize(16)
          .fontColor('#777777')
          .onClick(() => {
            postCardAction(this, {
              action: 'message',
              params: { msg: 'refresh' }
            })
          })
      }
      .width('100%')
      .margin({ bottom: 6 })

      Row() {
        Column() {
          Text('\uD83C\uDF21\uFE0F')
            .fontSize(18)
          Text(`${this.temperature}\u00B0C`)
            .fontSize(12)
            .fontWeight(FontWeight.Bold)
            .fontColor('#E07918')
          Text('温度')
            .fontSize(12)
            .fontColor('#777777')
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('\uD83D\uDCA7')
            .fontSize(18)
          Text(`${this.humidity}%`)
            .fontSize(12)
            .fontWeight(FontWeight.Bold)
            .fontColor('#2878C8')
          Text('湿度')
            .fontSize(12)
            .fontColor('#777777')
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text(this.lightOn ? '\uD83D\uDCA1' : '\uD83D\uDD0C')
            .fontSize(18)
          Text(this.lightOn ? '开启' : '关闭')
            .fontSize(12)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.lightOn ? '#E07918' : '#777777')
          Text('灯光')
            .fontSize(12)
            .fontColor('#777777')
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text(this.locked ? '\uD83D\uDD12' : '\uD83D\uDD13')
            .fontSize(18)
          Text(this.locked ? '锁定' : '解锁')
            .fontSize(12)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.locked ? '#16A064' : '#E07918')
          Text('门禁')
            .fontSize(12)
            .fontColor('#777777')
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)
      }
      .width('100%')

      Row() {
        Column() {
          Text(this.acOn ? '\u2744\uFE0F' : '\uD83D\uDD0C')
            .fontSize(18)
          Text(this.acOn ? '运行' : '关闭')
            .fontSize(12)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.acOn ? '#2878C8' : '#777777')
          Text('空调')
            .fontSize(12)
            .fontColor('#777777')
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text(this.curtainOpen ? '\u2600\uFE0F' : '\uD83E\uDE9B')
            .fontSize(18)
          Text(this.curtainOpen ? '开启' : '关闭')
            .fontSize(12)
            .fontWeight(FontWeight.Bold)
            .fontColor('#777777')
          Text('窗帘')
            .fontSize(12)
            .fontColor('#777777')
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text(this.humidifierOn ? '\u2728' : '\uD83D\uDD0C')
            .fontSize(18)
          Text(this.humidifierOn ? '运行' : '关闭')
            .fontSize(12)
            .fontWeight(FontWeight.Bold)
            .fontColor(this.humidifierOn ? '#2878C8' : '#777777')
          Text('加湿')
            .fontSize(12)
            .fontColor('#777777')
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)
      }
      .width('100%')
      .margin({ top: 4 })
    }
    .width('100%')
    .height('100%')
    .padding(10)
    .borderRadius(16)
    .backgroundColor(Color.White)
  }
}
