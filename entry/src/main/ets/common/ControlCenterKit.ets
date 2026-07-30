import { ControlCenterTheme } from './ControlCenterTheme'

@Component
export struct AppBottomNav {
  @Prop active: string = 'home'

  private navigate(key: string): void {
    if (key === this.active) {
      return
    }
    let route = ''
    if (key === 'home') {
      route = 'pages/DashboardPage'
    } else if (key === 'devices') {
      route = 'pages/DeviceManagePage'
    } else if (key === 'automation') {
      route = 'pages/RulesPage'
    } else if (key === 'profile') {
      route = 'pages/ProfilePage'
    }
    if (route) {
      try {
        this.getUIContext().getRouter().replaceUrl({ url: route })
      } catch (err) {
        console.error(err)
      }
    }
  }

  @Builder
  private icon(key: string) {
    if (key === 'home') {
      SymbolGlyph($r('sys.symbol.house'))
        .fontSize(20)
        .fontColor([this.active === key ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary])
    } else if (key === 'devices') {
      SymbolGlyph($r('sys.symbol.card_writer'))
        .fontSize(20)
        .fontColor([this.active === key ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary])
    } else if (key === 'automation') {
      SymbolGlyph($r('sys.symbol.repeat_1'))
        .fontSize(20)
        .fontColor([this.active === key ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary])
    } else {
      SymbolGlyph($r('sys.symbol.person_crop_circle_fill_1'))
        .fontSize(20)
        .fontColor([this.active === key ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary])
    }
  }

  @Builder
  private item(key: string, label: string) {
    Column() {
      this.icon(key)
      Text(label)
        .fontSize(12)
        .fontWeight(this.active === key ? FontWeight.Bold : FontWeight.Medium)
        .fontColor(this.active === key ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary)
        .margin({ top: 2 })
    }
    .layoutWeight(1)
    .height(50)
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .borderRadius(ControlCenterTheme.radiusChip)
    .backgroundColor(this.active === key ? ControlCenterTheme.accentSoft : '#00000000')
    .onClick(() => this.navigate(key))
  }

  build() {
    Row() {
      this.item('home', '首页')
      this.item('devices', '设备')
      this.item('automation', '自动化')
      this.item('profile', '我的')
    }
    .width('100%')
    .padding({ left: 10, right: 10, top: 6, bottom: 6 })
    .backgroundColor(ControlCenterTheme.surface)
    .border({ width: { top: 1 }, color: ControlCenterTheme.border })
  }
}

@Component
export struct SectionTitle {
  @Prop title: string = ''
  @Prop subtitle: string = ''
  @Prop trailing: string = ''

  build() {
    Row() {
      Column() {
        Text(this.title)
          .fontSize(ControlCenterTheme.sectionTitleSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        if (this.subtitle) {
          Text(this.subtitle)
            .fontSize(ControlCenterTheme.assistSize)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 4 })
        }
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)

      if (this.trailing) {
        Text(this.trailing)
          .fontSize(ControlCenterTheme.assistSize)
          .fontWeight(FontWeight.Medium)
          .fontColor(ControlCenterTheme.textSecondary)
          .padding({ left: 10, right: 10, top: 6, bottom: 6 })
          .borderRadius(ControlCenterTheme.radiusPill)
          .backgroundColor(ControlCenterTheme.surfaceMuted)
      }
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
  }
}

@Component
export struct StatusBanner {
  @Prop message: string = ''
  @Prop detail: string = ''
  @Prop tone: string = 'info'

  private bg(): string {
    switch (this.tone) {
      case 'success':
        return ControlCenterTheme.successSoft
      case 'warning':
        return ControlCenterTheme.warningSoft
      case 'danger':
        return ControlCenterTheme.dangerSoft
      default:
        return ControlCenterTheme.surfaceTint
    }
  }

  private fg(): string {
    switch (this.tone) {
      case 'success':
        return '#197D66'
      case 'warning':
        return '#9A651D'
      case 'danger':
        return '#A14D4D'
      default:
        return ControlCenterTheme.textPrimary
    }
  }

  build() {
    Row() {
      Text(this.message)
        .fontSize(ControlCenterTheme.bodySize)
        .fontWeight(FontWeight.Medium)
        .fontColor(this.fg())
        .layoutWeight(1)
      if (this.detail) {
        Text(this.detail)
          .fontSize(ControlCenterTheme.assistSize)
          .fontColor(this.fg())
          .opacity(0.72)
      }
    }
    .width('100%')
    .padding({ left: 14, right: 14, top: 12, bottom: 12 })
    .borderRadius(ControlCenterTheme.radiusInner)
    .backgroundColor(this.bg())
  }
}

@Component
export struct MetricChip {
  @Prop label: string = ''
  @Prop value: string = ''
  @Prop tone: string = 'neutral'
  @Prop inverse: boolean = false

  private bg(): string {
    if (this.inverse) {
      return '#FFFFFF14'
    }
    switch (this.tone) {
      case 'accent':
        return ControlCenterTheme.accentSoft
      case 'success':
        return ControlCenterTheme.successSoft
      case 'warning':
        return ControlCenterTheme.warningSoft
      case 'danger':
        return ControlCenterTheme.dangerSoft
      default:
        return ControlCenterTheme.surfaceMuted
    }
  }

  private valueColor(): string {
    if (this.inverse) {
      if (this.tone === 'success') {
        return ControlCenterTheme.success
      }
      if (this.tone === 'warning') {
        return ControlCenterTheme.warning
      }
      return ControlCenterTheme.textOnDark
    }

    switch (this.tone) {
      case 'accent':
        return ControlCenterTheme.accent
      case 'success':
        return '#209274'
      case 'warning':
        return '#A56A13'
      case 'danger':
        return '#B05C5C'
      default:
        return ControlCenterTheme.textPrimary
    }
  }

  private labelColor(): string {
    return this.inverse ? ControlCenterTheme.textOnDarkMuted : ControlCenterTheme.textSecondary
  }

  build() {
    Column() {
      Text(this.label)
        .fontSize(ControlCenterTheme.assistSize)
        .fontColor(this.labelColor())
      Text(this.value)
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .fontColor(this.valueColor())
        .margin({ top: 8 })
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
    }
    .padding({ left: 14, right: 14, top: 12, bottom: 12 })
    .borderRadius(ControlCenterTheme.radiusInner)
    .backgroundColor(this.bg())
    .alignItems(HorizontalAlign.Start)
  }
}
