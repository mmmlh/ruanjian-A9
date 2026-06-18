import { AbilityConstant, UIAbility, Want } from '@kit.AbilityKit'
import { hilog } from '@kit.PerformanceAnalysisKit'
import { window } from '@kit.ArkUI'

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onCreate')
  }

  onDestroy(): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onDestroy')
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onWindowStageCreate')
    windowStage.loadContent('pages/LoginPage', (err) => {
      if (err.code) {
        hilog.error(0x0000, 'SmartHome', 'Failed to load content: %{public}s', JSON.stringify(err))
        return
      }
      hilog.info(0x0000, 'SmartHome', 'Succeeded in loading content')
    })
  }

  onWindowStageDestroy(): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onWindowStageDestroy')
  }

  onForeground(): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onForeground')
  }

  onBackground(): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onBackground')
  }
}
