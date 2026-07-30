import AbilityConstant from '@ohos.app.ability.AbilityConstant'
import UIAbility from '@ohos.app.ability.UIAbility'
import Want from '@ohos.app.ability.Want'
import hilog from '@ohos.hilog'
import window from '@ohos.window'
import { initPreferences } from '../common/SecureStorage'
import { setSessionExpiredHandler } from '../common/ApiClient'
import { disconnectWS } from '../common/MqttClient'

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onCreate')
    initPreferences(this.context)
  }

  onDestroy(): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onDestroy')
    setSessionExpiredHandler(null)
    disconnectWS()
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    hilog.info(0x0000, 'SmartHome', 'Ability onWindowStageCreate')
    windowStage.loadContent('pages/LoginPage', (err) => {
      if (err.code) {
        hilog.error(0x0000, 'SmartHome', 'Failed to load content: %{public}s', JSON.stringify(err))
        return
      }
      hilog.info(0x0000, 'SmartHome', 'Succeeded in loading content')
      setSessionExpiredHandler(() => {
        disconnectWS()
        windowStage.getMainWindowSync().getUIContext().getRouter().replaceUrl({ url: 'pages/LoginPage' })
      })
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
