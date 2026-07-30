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
  private item(key: string, label: string) {
    Button() {
      Column() {
        if (key === 'home') {
          Image($r('app.media.nav_home'))
            .width(20)
            .height(20)
            .opacity(this.active === key ? 1 : 0.48)
        } else if (key === 'devices') {
          Image($r('app.media.nav_devices'))
            .width(20)
            .height(20)
            .opacity(this.active === key ? 1 : 0.48)
        } else if (key === 'automation') {
          Image($r('app.media.nav_automation'))
            .width(20)
            .height(20)
            .opacity(this.active === key ? 1 : 0.48)
        } else {
          Image($r('app.media.nav_profile'))
            .width(20)
            .height(20)
            .opacity(this.active === key ? 1 : 0.48)
        }
        Text(label)
          .fontSize(12)
          .fontWeight(this.active === key ? FontWeight.Bold : FontWeight.Medium)
          .fontColor(this.active === key ? ControlCenterTheme.textPrimary : ControlCenterTheme.textSecondary)
          .margin({ top: 2 })
      }
      .width('100%')
      .height('100%')
      .justifyContent(FlexAlign.Center)
      .alignItems(HorizontalAlign.Center)
    }
    .layoutWeight(1)
    .height(ControlCenterTheme.tapTarget)
    .padding(0)
    .borderRadius(ControlCenterTheme.radiusInner)
    .backgroundColor(this.active === key ? ControlCenterTheme.accentSoft : '#00000000')
    .accessibilityText(this.active === key ? label + '，当前页面' : label)
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
    .padding({ left: 10, right: 10, top: 10, bottom: 10 })
    .backgroundColor(ControlCenterTheme.surface)
    .border({ width: { top: 1 }, color: ControlCenterTheme.border })
  }
}

@Component
export struct AppTopBar {
  @Prop title: string = ''
  @Prop subtitle: string = ''
  @Prop showBack: boolean = false
  @Prop actionLabel: string = ''
  @Prop actionType: string = 'refresh'
  @Prop onAction: () => void = () => {}

  build() {
    Row() {
      if (this.showBack) {
        Button() {
          Row() {
            Image($r('app.media.action_back'))
              .width(20)
              .height(20)
          }
          .width('100%')
          .height('100%')
          .justifyContent(FlexAlign.Center)
          .alignItems(VerticalAlign.Center)
        }
        .width(ControlCenterTheme.tapTarget)
        .height(ControlCenterTheme.tapTarget)
        .padding(0)
        .borderRadius(ControlCenterTheme.radiusInner)
        .backgroundColor(ControlCenterTheme.surfaceMuted)
        .margin({ right: ControlCenterTheme.spaceSm })
        .accessibilityText('返回')
        .onClick(() => this.getUIContext().getRouter().back())
      }

      Column() {
        Text(this.title)
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
          .maxLines(1)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
        if (this.subtitle) {
          Text(this.subtitle)
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .maxLines(1)
            .textOverflow({ overflow: TextOverflow.Ellipsis })
            .margin({ top: ControlCenterTheme.spaceXs })
        }
      }
      .layoutWeight(1)
      .alignItems(HorizontalAlign.Start)

      if (this.actionLabel) {
        Button() {
          Row() {
            if (this.actionType === 'add') {
              Image($r('app.media.action_add'))
                .width(18)
                .height(18)
            } else {
              Image($r('app.media.action_refresh'))
                .width(18)
                .height(18)
            }
            Text(this.actionLabel)
              .fontSize(13)
              .fontWeight(FontWeight.Medium)
              .fontColor(ControlCenterTheme.textPrimary)
              .margin({ left: ControlCenterTheme.spaceXs })
          }
          .height('100%')
          .justifyContent(FlexAlign.Center)
          .alignItems(VerticalAlign.Center)
        }
        .height(ControlCenterTheme.tapTarget)
        .padding({ left: ControlCenterTheme.spaceMd, right: ControlCenterTheme.spaceMd })
        .borderRadius(ControlCenterTheme.radiusInner)
        .backgroundColor(ControlCenterTheme.accentSoft)
        .margin({ left: ControlCenterTheme.spaceSm })
        .accessibilityText(this.actionLabel)
        .onClick(() => this.onAction())
      }
    }
    .width('100%')
    .alignItems(VerticalAlign.Center)
  }
}

@Component
export struct PrimaryButton {
  @Prop label: string = ''
  @Prop isEnabled: boolean = true
  @Prop onAction: () => void = () => {}

  build() {
    Button(this.label)
      .width('100%')
      .height(ControlCenterTheme.tapTarget)
      .fontSize(14)
      .fontWeight(FontWeight.Bold)
      .fontColor(ControlCenterTheme.surface)
      .backgroundColor(ControlCenterTheme.accent)
      .borderRadius(ControlCenterTheme.radiusInner)
      .enabled(this.isEnabled)
      .opacity(this.isEnabled ? 1 : 0.42)
      .onClick(() => this.onAction())
  }
}

@Component
export struct SecondaryButton {
  @Prop label: string = ''
  @Prop isEnabled: boolean = true
  @Prop onAction: () => void = () => {}

  build() {
    Button(this.label)
      .width('100%')
      .height(ControlCenterTheme.tapTarget)
      .fontSize(14)
      .fontWeight(FontWeight.Medium)
      .fontColor(ControlCenterTheme.accent)
      .backgroundColor(ControlCenterTheme.surfaceMuted)
      .border({ width: 1, color: ControlCenterTheme.borderStrong })
      .borderRadius(ControlCenterTheme.radiusInner)
      .enabled(this.isEnabled)
      .opacity(this.isEnabled ? 1 : 0.42)
      .onClick(() => this.onAction())
  }
}

@Component
export struct EmptyState {
  @Prop title: string = ''
  @Prop detail: string = ''
  @Prop actionLabel: string = ''
  @Prop actionEnabled: boolean = true
  @Prop onAction: () => void = () => {}

  build() {
    Column() {
      Text(this.title)
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
      if (this.detail) {
        Text(this.detail)
          .fontSize(12)
          .fontColor(ControlCenterTheme.textSecondary)
          .textAlign(TextAlign.Center)
          .margin({ top: ControlCenterTheme.spaceSm })
      }
      if (this.actionLabel) {
        Button(this.actionLabel)
          .height(ControlCenterTheme.tapTarget)
          .padding({ left: ControlCenterTheme.spaceLg, right: ControlCenterTheme.spaceLg })
          .fontSize(14)
          .fontWeight(FontWeight.Medium)
          .fontColor(ControlCenterTheme.textPrimary)
          .backgroundColor(ControlCenterTheme.accentSoft)
          .borderRadius(ControlCenterTheme.radiusInner)
          .enabled(this.actionEnabled)
          .opacity(this.actionEnabled ? 1 : 0.42)
          .margin({ top: ControlCenterTheme.spaceMd })
          .onClick(() => this.onAction())
      }
    }
    .width('100%')
    .padding({ left: ControlCenterTheme.spaceLg, right: ControlCenterTheme.spaceLg,
      top: ControlCenterTheme.spaceXl, bottom: ControlCenterTheme.spaceXl })
    .alignItems(HorizontalAlign.Center)
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(ControlCenterTheme.surface)
  }
}

@Component
export struct ConfirmPanel {
  @Prop title: string = ''
  @Prop detail: string = ''
  @Prop confirmLabel: string = '确认'
  @Prop cancelLabel: string = '取消'
  @Prop danger: boolean = true
  @Prop onCancel: () => void = () => {}
  @Prop onConfirm: () => void = () => {}

  build() {
    Column() {
      Text(this.title)
        .width('100%')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
      if (this.detail) {
        Text(this.detail)
          .width('100%')
          .fontSize(12)
          .fontColor(ControlCenterTheme.textPrimary)
          .margin({ top: ControlCenterTheme.spaceSm })
      }
      Row() {
        Button(this.cancelLabel)
          .layoutWeight(1)
          .height(ControlCenterTheme.tapTarget)
          .fontSize(14)
          .fontColor(ControlCenterTheme.textPrimary)
          .backgroundColor(ControlCenterTheme.surface)
          .borderRadius(ControlCenterTheme.radiusInner)
          .onClick(() => this.onCancel())
        Blank().width(ControlCenterTheme.spaceSm)
        Button(this.confirmLabel)
          .layoutWeight(1)
          .height(ControlCenterTheme.tapTarget)
          .fontSize(14)
          .fontColor(ControlCenterTheme.surface)
          .backgroundColor(this.danger ? ControlCenterTheme.danger : ControlCenterTheme.warning)
          .borderRadius(ControlCenterTheme.radiusInner)
          .onClick(() => this.onConfirm())
      }
      .width('100%')
      .margin({ top: ControlCenterTheme.spaceMd })
    }
    .width('100%')
    .padding(ControlCenterTheme.spaceLg)
    .alignItems(HorizontalAlign.Start)
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(this.danger ? ControlCenterTheme.dangerSoft : ControlCenterTheme.warningSoft)
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
          .fontSize(18)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        if (this.subtitle) {
          Text(this.subtitle)
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 4 })
        }
      }
      .alignItems(HorizontalAlign.Start)
      .layoutWeight(1)

      if (this.trailing) {
        Text(this.trailing)
          .fontSize(12)
          .fontWeight(FontWeight.Medium)
          .fontColor(ControlCenterTheme.textPrimary)
          .padding({ left: 10, right: 10, top: 6, bottom: 6 })
          .borderRadius(ControlCenterTheme.radiusPill)
          .backgroundColor(ControlCenterTheme.surfaceTint)
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

  private toneLabel(): string {
    switch (this.tone) {
      case 'success':
        return '成功'
      case 'warning':
        return '警告'
      case 'danger':
        return '错误'
      default:
        return '提示'
    }
  }

  build() {
    Row() {
      Text(this.toneLabel())
        .fontSize(12)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ right: ControlCenterTheme.spaceSm })
      Column() {
        Text(this.message)
          .width('100%')
          .fontSize(13)
          .fontWeight(FontWeight.Medium)
          .fontColor(ControlCenterTheme.textPrimary)
        if (this.detail) {
          Text(this.detail)
            .width('100%')
            .fontSize(12)
            .fontColor(ControlCenterTheme.textPrimary)
            .margin({ top: ControlCenterTheme.spaceXs })
        }
      }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Start)
    }
    .width('100%')
    .alignItems(VerticalAlign.Top)
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
        return ControlCenterTheme.success
      case 'warning':
        return ControlCenterTheme.warning
      case 'danger':
        return ControlCenterTheme.danger
      default:
        return ControlCenterTheme.textPrimary
    }
  }

  private labelColor(): string {
    return this.inverse ? ControlCenterTheme.textOnDarkMuted : ControlCenterTheme.textPrimary
  }

  build() {
    Column() {
      Text(this.label)
        .fontSize(12)
        .fontColor(this.labelColor())
      Text(this.value)
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .fontColor(this.valueColor())
        .margin({ top: 8 })
        .maxLines(1)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
    }
    .padding({ left: 14, right: 14, top: 14, bottom: 14 })
    .borderRadius(ControlCenterTheme.radiusInner)
    .backgroundColor(this.bg())
    .alignItems(HorizontalAlign.Start)
  }
}
