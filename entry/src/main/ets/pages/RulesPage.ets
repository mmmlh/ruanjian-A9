import { createRule, deleteRule, getRuleOptions, getRules, toggleRule } from '../common/ApiClient'
import { ControlCenterTheme } from '../common/ControlCenterTheme'
import { AppBottomNav, SectionTitle, StatusBanner, MetricChip } from '../common/ControlCenterKit'
import { UiText } from '../common/UiText'
import { AutomationRule, RuleOptions, RuleTargetOption, RuleTriggerOption, RuleOperatorOption } from '../model/DeviceModel'

function localizeMessage(message: string, fallback: string): string {
  if (!message) {
    return fallback
  }
  if (/[\u4e00-\u9fff]/.test(message)) {
    return message
  }
  let transportMessage = UiText.mapTransportMessage(message)
  return transportMessage !== message ? transportMessage : fallback
}

@Entry
@Component
struct RulesPage {
  @State rules: AutomationRule[] = []
  @State loading: boolean = false
  @State dlg: boolean = false
  @State nm: string = ''
  @State tr: string = ''
  @State fl: string = 'value'
  @State op: string = 'gt'
  @State vl: string = '28'
  @State targetId: number = 0
  @State targetType: string = ''
  @State targetRoom: string = 'same'
  @State an: string = ''
  @State modeValue: string = 'cool'
  @State tempValue: number = 26
  @State brightnessValue: number = 80
  @State targetHumidityValue: number = 60
  @State levelValue: number = 2
  @State optionsLoaded: boolean = false
  @State ruleOptions: RuleOptions = new RuleOptions()
  @State errorMessage: string = ''
  @State ruleTab: number = 0
  @State deleteTargetId: number = -1
  @State deleteTargetName: string = ''

  aboutToAppear(): void {
    this.ld()
  }

  async ld(): Promise<void> {
    this.loading = true
    this.errorMessage = ''
    try {
      if (!this.optionsLoaded) {
        await this.loadOptions()
      }
      this.rules = await getRules()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '加载自动化规则失败')
    } finally {
      this.loading = false
    }
  }

  async loadOptions(): Promise<void> {
    this.ruleOptions = await getRuleOptions()
    this.optionsLoaded = true
    if (this.ruleOptions.triggers.length > 0) {
      this.tr = this.ruleOptions.triggers[0].value
      this.fl = this.ruleOptions.triggers[0].field
    }
    if (this.ruleOptions.targets.length > 0) {
      let first = this.ruleOptions.targets[0]
      this.targetId = first.device_id
      this.targetType = first.type
      this.targetRoom = first.room_name ? first.room_name.toLowerCase().replace(/\s+/g, '') : 'same'
      if (first.actions.length > 0) {
        this.an = first.actions[0]
      }
    }
  }

  async dT(id: number): Promise<void> {
    try {
      await toggleRule(id)
      this.rules = await getRules()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '切换规则状态失败')
    }
  }

  async dD(id: number): Promise<void> {
    try {
      await deleteRule(id)
      this.rules = await getRules()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '删除规则失败')
    }
  }

  requestDelete(rule: AutomationRule): void {
    this.deleteTargetId = rule.id
    this.deleteTargetName = rule.name
  }

  async confirmDelete(): Promise<void> {
    let id = this.deleteTargetId
    this.deleteTargetId = -1
    this.deleteTargetName = ''
    if (id > 0) {
      await this.dD(id)
    }
  }

  buildConditionJson(): string {
    let triggerValue: Object = this.tr === 'pir_sensor' ? (this.vl === 'true') : Number(this.vl)
    return JSON.stringify({
      'trigger': this.tr,
      'field': this.fl,
      'operator': this.op,
      'value': triggerValue
    })
  }

  buildActionJson(): string {
    let params: Record<string, Object> = {}
    if (this.targetType === 'light' && this.an === 'set') {
      params['power'] = 'on'
      params['brightness'] = this.brightnessValue
    } else if (this.targetType === 'ac' && this.an === 'set') {
      params['power'] = 'on'
      params['mode'] = this.modeValue
      params['temp'] = this.tempValue
    } else if (this.targetType === 'humidifier' && this.an === 'set') {
      params['power'] = 'on'
      params['level'] = this.levelValue
      params['target_humidity'] = this.targetHumidityValue
    } else if (this.targetType === 'curtain' && this.an === 'set') {
      params['position'] = 100
    }

    return JSON.stringify([{
      'device_id': this.targetId,
      'device_type': this.targetType,
      'room_id': this.targetRoom || 'same',
      'action': this.an,
      'params': params
    }])
  }

  resetDialog(): void {
    this.nm = ''
    this.vl = '28'
    this.modeValue = 'cool'
    this.tempValue = 26
    this.brightnessValue = 80
    this.targetHumidityValue = 60
    this.levelValue = 2
  }

  async dC(): Promise<void> {
    this.errorMessage = ''
    if (!this.nm.trim()) {
      this.errorMessage = '规则名称不能为空'
      return
    }
    if (!this.tr || !this.targetType || !this.an) {
      this.errorMessage = '请完整选择触发条件和执行动作'
      return
    }
    if (this.tr === 'pir_sensor' && this.op !== 'eq' && this.op !== 'neq') {
      this.errorMessage = '人体传感规则仅支持等于和不等于'
      return
    }
    if (this.tr !== 'pir_sensor') {
      if (!this.vl.trim()) {
        this.errorMessage = '阈值不能为空'
        return
      }
      let threshold = Number(this.vl)
      if (!Number.isFinite(threshold)) {
        this.errorMessage = '阈值必须是数字'
        return
      }
    }
    try {
      await createRule(this.nm.trim(), this.buildConditionJson(), this.buildActionJson())
      this.resetDialog()
      this.dlg = false
      this.rules = await getRules()
    } catch (err) {
      this.errorMessage = localizeMessage((err as Error).message, '创建规则失败')
    }
  }

  enabledCount(): number {
    let total = 0
    for (let i = 0; i < this.rules.length; i++) {
      if (this.rules[i].enabled === 1) {
        total++
      }
    }
    return total
  }

  operatorLabel(value: string): string {
    for (let i = 0; i < this.ruleOptions.operators.length; i++) {
      let option = this.ruleOptions.operators[i]
      if (option.value === value) {
        if (option.value === 'eq') return '等于'
        if (option.value === 'neq') return '不等于'
        if (option.value === 'gt') return '大于'
        if (option.value === 'gte') return '大于等于'
        if (option.value === 'lt') return '小于'
        if (option.value === 'lte') return '小于等于'
        return option.label
      }
    }
    return value
  }

  triggerLabel(value: string): string {
    for (let i = 0; i < this.ruleOptions.triggers.length; i++) {
      let trigger = this.ruleOptions.triggers[i]
      if (trigger.value === value) {
        if (/[\u4e00-\u9fff]/.test(trigger.label)) {
          return trigger.label
        }
        return this.deviceTypeLabel(trigger.value)
      }
    }
    if (value === 'temperature_sensor') return '温度传感器'
    if (value === 'humidity_sensor') return '湿度传感器'
    if (value === 'pir_sensor') return '人体传感器'
    if (/[\u4e00-\u9fff]/.test(value)) return value
    return '传感器'
  }

  deviceTypeLabel(value: string): string {
    if (value === 'light') return '灯光'
    if (value === 'ac') return '空调'
    if (value === 'door_lock') return '门锁'
    if (value === 'curtain') return '窗帘'
    if (value === 'humidifier') return '加湿器'
    if (value === 'temperature_sensor') return '温度传感器'
    if (value === 'humidity_sensor') return '湿度传感器'
    if (value === 'pir_sensor') return '人体传感器'
    if (/[\u4e00-\u9fff]/.test(value)) return value
    return '设备'
  }

  actionLabel(value: string): string {
    if (value === 'on') return '开启'
    if (value === 'off') return '关闭'
    if (value === 'set') return '设置'
    if (value === 'unlock') return '解锁'
    if (value === 'lock') return '上锁'
    if (value === 'open') return '打开'
    if (value === 'close') return '关闭'
    if (/[\u4e00-\u9fff]/.test(value)) return value
    return '自定义动作'
  }

  triggerValueLabel(trigger: string, value: Object): string {
    if (trigger === 'pir_sensor') {
      return Boolean(value) ? '检测到活动' : '区域空闲'
    }
    return String(value)
  }

  cs(rule: AutomationRule): string {
    try {
      let condition = JSON.parse(rule.condition_json) as Record<string, Object>
      return '如果 ' + this.triggerLabel(String(condition['trigger'])) + ' ' + this.operatorLabel(String(condition['operator'])) + ' ' + this.triggerValueLabel(String(condition['trigger']), condition['value'])
    } catch (e) {
      return '条件信息不可用'
    }
  }

  as(rule: AutomationRule): string {
    try {
      let actions = JSON.parse(rule.action_json) as Array<Object>
      if (actions.length === 0) return '动作信息不可用'
      let first = actions[0] as Record<string, Object>
      return '则 ' + this.deviceTypeLabel(String(first['device_type'])) + ' 执行“' + this.actionLabel(String(first['action'])) + '”'
    } catch (e) {
      return '动作信息不可用'
    }
  }

  currentTarget(): RuleTargetOption | null {
    for (let i = 0; i < this.ruleOptions.targets.length; i++) {
      if (this.ruleOptions.targets[i].device_id === this.targetId) {
        return this.ruleOptions.targets[i]
      }
    }
    return null
  }

  availableActions(): string[] {
    let target = this.currentTarget()
    if (target) {
      return target.actions
    }
    let mapped = this.ruleOptions.actions[this.targetType]
    return mapped !== undefined && mapped !== null ? mapped : []
  }

  availableOperators(): RuleOperatorOption[] {
    if (this.tr !== 'pir_sensor') {
      return this.ruleOptions.operators
    }

    let filtered: RuleOperatorOption[] = []
    for (let i = 0; i < this.ruleOptions.operators.length; i++) {
      let option = this.ruleOptions.operators[i]
      if (option.value === 'eq' || option.value === 'neq') {
        filtered.push(option)
      }
    }
    return filtered
  }

  pickTarget(target: RuleTargetOption): void {
    this.targetId = target.device_id
    this.targetType = target.type
    this.targetRoom = target.room_name ? target.room_name.toLowerCase().replace(/\s+/g, '') : 'same'
    if (target.actions.length > 0) {
      this.an = target.actions[0]
    }
  }

  pickTrigger(value: string, field: string): void {
    this.tr = value
    this.fl = field
    if (value === 'pir_sensor') {
      if (this.op !== 'eq' && this.op !== 'neq') {
        this.op = 'eq'
      }
      this.vl = 'true'
    } else if (this.vl === 'true' || this.vl === 'false') {
      this.vl = '28'
    }
  }

  showParams(): boolean {
    return this.an === 'set'
  }

  selectedTrigger(): RuleTriggerOption | null {
    for (let i = 0; i < this.ruleOptions.triggers.length; i++) {
      let trigger = this.ruleOptions.triggers[i]
      if (trigger.value === this.tr && trigger.field === this.fl) {
        return trigger
      }
    }
    return null
  }

  previewCondition(): string {
    let trigger = this.selectedTrigger()
    let room = trigger && trigger.room_name ? trigger.room_name : '当前房间'
    let value = this.tr === 'pir_sensor' ? this.triggerValueLabel(this.tr, this.vl === 'true') : this.vl
    return room + ' 的 ' + this.triggerLabel(this.tr) + ' ' + this.operatorLabel(this.op) + ' ' + value
  }

  previewAction(): string {
    let target = this.currentTarget()
    let targetLabel = target ? target.room_name + ' · ' + this.deviceTypeLabel(target.type) : this.deviceTypeLabel(this.targetType)
    let detail = this.actionLabel(this.an)
    if (this.an === 'set') {
      if (this.targetType === 'light') {
        detail = detail + ' 亮度 ' + this.brightnessValue.toString() + '%'
      } else if (this.targetType === 'ac') {
        detail = detail + ' 温度 ' + this.tempValue.toString() + '°C'
      } else if (this.targetType === 'humidifier') {
        detail = detail + ' 湿度 ' + this.targetHumidityValue.toString() + '%'
      } else if (this.targetType === 'curtain') {
        detail = detail + ' 到全开'
      }
    }
    return targetLabel + ' -> ' + detail
  }

  build() {
    Stack() {
      Column() {
        this.buildTopBar()

      if (this.errorMessage) {
        StatusBanner({
          message: this.errorMessage,
          detail: '请检查规则内容或稍后重试',
          tone: 'danger'
        }).margin({ top: 12, left: 16, right: 16 })
      }

      if (this.loading && this.rules.length === 0) {
        this.buildLoading()
      } else if (this.rules.length === 0) {
        this.buildEmpty()
      } else {
        Scroll() {
          Column() {
            this.buildMijiaRulesHero()
            this.buildRuleTabs()
            this.buildRuleList()
            this.buildRecommendedScenes()
          }
          .padding({ left: 16, right: 16, top: 16, bottom: 28 })
        }
        .layoutWeight(1)
        .scrollBar(BarState.Off)
      }

        if (!this.dlg && this.deleteTargetId < 0) {
          AppBottomNav({ active: 'automation' })
        }
      }
      .width('100%')
      .height('100%')

      if (this.dlg) {
        this.buildDialog()
      }

      if (this.deleteTargetId > 0) {
        this.buildDeleteConfirm()
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor(ControlCenterTheme.pageBg)
  }

  @Builder buildTopBar() {
    Row() {
      Column() {
        Text('自动化')
          .fontSize(ControlCenterTheme.pageTitleSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        Text('让设备按条件自动响应')
          .fontSize(ControlCenterTheme.assistSize)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 4 })
      }
      .alignItems(HorizontalAlign.Start)
      Blank()
      Button() {
        Row() {
          SymbolGlyph($r('sys.symbol.plus'))
            .fontSize(18)
            .fontColor([ControlCenterTheme.accent])
          Text('新增规则')
            .fontSize(ControlCenterTheme.assistSize)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.accent)
            .margin({ left: 5 })
        }
      }
        .type(ButtonType.Capsule)
        .height(ControlCenterTheme.tapTarget)
        .borderRadius(ControlCenterTheme.radiusPill)
        .backgroundColor(ControlCenterTheme.accentSoft)
        .onClick(() => {
          this.errorMessage = ''
          this.dlg = true
        })
    }
    .width('100%')
    .padding({ left: 16, right: 16, top: 14, bottom: 0 })
    .alignItems(VerticalAlign.Center)
  }

  filteredRules(): AutomationRule[] {
    if (this.ruleTab === 0) {
      return this.rules
    }
    let enabled: AutomationRule[] = []
    for (let index = 0; index < this.rules.length; index++) {
      if (this.rules[index].enabled === 1) {
        enabled.push(this.rules[index])
      }
    }
    return enabled
  }

  @Builder buildMijiaRulesHero() {
    Column() {
      Row() {
        Column() {
          Text('规则概览')
            .fontSize(ControlCenterTheme.sectionTitleSize)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('当前规则运行状态')
            .fontSize(ControlCenterTheme.assistSize)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 5 })
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1)
        Text(this.enabledCount().toString() + '/' + this.rules.length.toString())
          .fontSize(22)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.accent)
      }
      .width('100%')
      Row() {
        MetricChip({ label: '已启用', value: this.enabledCount().toString(), tone: 'success' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({ label: '全部规则', value: this.rules.length.toString(), tone: 'accent' }).layoutWeight(1)
      }
      .width('100%')
      .margin({ top: 14 })
    }
    .width('100%')
    .padding(16)
    .borderRadius(ControlCenterTheme.radiusHero)
    .backgroundColor(ControlCenterTheme.surface)
    .border({ width: 1, color: ControlCenterTheme.border })
    .shadow({ radius: 10, color: ControlCenterTheme.shadowSoft, offsetY: 4 })
  }

  @Builder buildRuleTabs() {
    Row() {
      this.ruleTabChip('全部', 0, () => { this.ruleTab = 0 })
      this.ruleTabChip('已启用', 1, () => { this.ruleTab = 1 })
    }
    .width('100%')
    .padding(4)
    .borderRadius(ControlCenterTheme.radiusInner)
    .backgroundColor(ControlCenterTheme.surfaceMuted)
    .margin({ top: 16 })
  }

  @Builder ruleTabChip(label: string, tabIndex: number, action: () => void) {
    Text(label)
      .fontSize(13)
      .fontWeight(this.ruleTab === tabIndex ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(this.ruleTab === tabIndex ? ControlCenterTheme.accent : ControlCenterTheme.textSecondary)
      .textAlign(TextAlign.Center)
      .layoutWeight(1)
      .height(ControlCenterTheme.tapTarget)
      .padding({ top: 13, bottom: 13 })
      .borderRadius(ControlCenterTheme.radiusPill)
      .backgroundColor(this.ruleTab === tabIndex ? ControlCenterTheme.surface : '#00000000')
      .border({ width: this.ruleTab === tabIndex ? 1 : 0, color: this.ruleTab === tabIndex ? ControlCenterTheme.border : '#00000000' })
      .shadow(this.ruleTab === tabIndex ? { radius: 6, color: ControlCenterTheme.shadowSoft, offsetY: 2 } : { radius: 0, color: '#00000000', offsetY: 0 })
      .animation({ duration: 180, curve: Curve.EaseOut })
      .onClick(action)
  }

  @Builder buildHero() {
    Column() {
      Row() {
        Column() {
          Text('规则中控面板')
            .fontSize(20)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('把传感器条件和设备动作组合成可读、可信的自动化。')
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 5 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Start)

        Text(this.rules.length.toString() + ' 条')
          .fontSize(12)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.accent)
          .padding({ left: 10, right: 10, top: 6, bottom: 6 })
          .borderRadius(ControlCenterTheme.radiusPill)
          .backgroundColor(ControlCenterTheme.accentSoft)
      }
      .width('100%')

      Row() {
        MetricChip({ label: '启用中', value: this.enabledCount().toString(), tone: 'success' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({ label: '总规则', value: this.rules.length.toString(), tone: 'accent' }).layoutWeight(1)
        Blank().width(10)
        MetricChip({ label: '可选设备', value: this.ruleOptions.targets.length.toString(), tone: 'warning' }).layoutWeight(1)
      }
      .width('100%')
      .margin({ top: 18 })

    }
    .width('100%')
    .padding(20)
    .borderRadius(ControlCenterTheme.radiusHero)
    .backgroundColor(ControlCenterTheme.surface)
    .border({ width: 1, color: ControlCenterTheme.border })
    .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
  }

  @Builder buildRuleList() {
    Column() {
      SectionTitle({
        title: '已创建规则',
        subtitle: '条件与执行动作一目了然',
        trailing: this.enabledCount().toString() + ' 条启用'
      })

      List() {
        ForEach(this.filteredRules(), (rule: AutomationRule) => {
          ListItem() {
            Column() {
              Row() {
                Column() {
                  Text(rule.name)
                    .fontSize(16)
                    .fontWeight(FontWeight.Bold)
                    .fontColor(ControlCenterTheme.textPrimary)
                  Text(this.cs(rule))
                    .fontSize(12)
                    .fontColor(ControlCenterTheme.textSecondary)
                    .margin({ top: 8 })
                  Text(this.as(rule))
                    .fontSize(12)
                    .fontColor(ControlCenterTheme.textSecondary)
                    .margin({ top: 4 })
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Start)

              }
              .width('100%')

              Row() {
                Toggle({ type: ToggleType.Switch, isOn: rule.enabled === 1 })
                  .selectedColor(ControlCenterTheme.accent)
                  .accessibilityText(rule.enabled === 1 ? '停用' + rule.name : '启用' + rule.name)
                  .onChange((isOn: boolean) => { this.dT(rule.id) })
                Blank()
                Button() {
                  SymbolGlyph($r('sys.symbol.trash'))
                    .fontSize(20)
                    .fontColor([ControlCenterTheme.danger])
                }
                  .width(ControlCenterTheme.tapTarget)
                  .height(ControlCenterTheme.tapTarget)
                  .borderRadius(ControlCenterTheme.radiusInner)
                  .backgroundColor(ControlCenterTheme.dangerSoft)
                  .accessibilityText('删除' + rule.name)
                  .onClick(() => this.requestDelete(rule))
              }
              .width('100%')
              .margin({ top: 14 })
            }
            .padding(16)
            .borderRadius(ControlCenterTheme.radiusCard)
            .backgroundColor(ControlCenterTheme.surface)
            .border({ width: 1, color: ControlCenterTheme.border })
            .shadow({ radius: 10, color: ControlCenterTheme.shadowSoft, offsetY: 4 })
          }
          .padding({ top: 12 })
        }, (rule: AutomationRule) => rule.id.toString())
      }
      .width('100%')
      .margin({ top: 12 })
      .layoutWeight(1)
    }
    .width('100%')
    .margin({ top: 20 })
  }

  @Builder buildRecommendedScenes() {
    Column() {
      Text('推荐场景')
        .fontSize(17)
        .fontWeight(FontWeight.Bold)
        .fontColor(ControlCenterTheme.textPrimary)
      Column() {
        Text('空气干燥时自动加湿')
          .fontSize(15)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        Text('根据湿度传感器读数启动加湿器')
          .fontSize(12)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 7 })
        Text('一键创建 ›')
          .fontSize(12)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.accent)
          .margin({ top: 12 })
      }
      .width('100%')
      .padding(16)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.accentSoft)
      .margin({ top: 12 })
      .onClick(() => { this.dlg = true })
    }
    .width('100%')
    .margin({ top: 20 })
  }

  @Builder buildLoading() {
    Column() {
      LoadingProgress().width(30).height(30).color(ControlCenterTheme.accent)
      Text('正在加载自动化规则...')
        .fontSize(13)
        .fontColor(ControlCenterTheme.textSecondary)
        .margin({ top: 14 })
    }
    .width('100%')
    .layoutWeight(1)
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
  }

  @Builder buildEmpty() {
    Scroll() {
      Column() {
        this.buildHero()
        Column() {
          Text('还没有创建自动化规则')
            .fontSize(17)
            .fontWeight(FontWeight.Bold)
            .fontColor(ControlCenterTheme.textPrimary)
          Text('先创建一条“如果 / 则”规则，让设备自动协同。')
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .margin({ top: 6 })
          Button('创建第一条规则')
            .type(ButtonType.Capsule)
            .width('100%')
            .height(48)
            .fontSize(15)
            .fontWeight(FontWeight.Bold)
            .backgroundColor(ControlCenterTheme.accent)
            .fontColor('#FFFFFF')
            .borderRadius(16)
            .margin({ top: 18 })
            .onClick(() => {
              this.errorMessage = ''
              this.dlg = true
            })
        }
        .width('100%')
        .padding(20)
        .borderRadius(ControlCenterTheme.radiusCard)
        .backgroundColor(ControlCenterTheme.surface)
        .border({ width: 1, color: ControlCenterTheme.border })
        .shadow({ radius: 18, color: ControlCenterTheme.shadowSoft, offsetY: 8 })
        .margin({ top: 20 })
      }
      .padding({ left: 16, right: 16, top: 16, bottom: 28 })
    }
    .width('100%')
    .layoutWeight(1)
    .scrollBar(BarState.Off)
  }

  isChoiceSelected(group: number, value: string): boolean {
    if (group === 0) {
      return this.tr + '|' + this.fl === value
    }
    if (group === 1) {
      return this.op === value
    }
    if (group === 2) {
      return this.vl === value
    }
    if (group === 3) {
      return this.targetId.toString() === value
    }
    return this.an === value
  }

  @Builder buildChoiceChip(label: string, group: number, value: string, action: () => void) {
    Text(label)
      .fontSize(12)
      .fontWeight(this.isChoiceSelected(group, value) ? FontWeight.Bold : FontWeight.Medium)
      .fontColor(this.isChoiceSelected(group, value) ? ControlCenterTheme.textOnDark : ControlCenterTheme.textSecondary)
      .padding({ left: 14, right: 14, top: 10, bottom: 10 })
      .height(ControlCenterTheme.tapTarget)
      .borderRadius(ControlCenterTheme.radiusChip)
      .backgroundColor(this.isChoiceSelected(group, value) ? ControlCenterTheme.accent : ControlCenterTheme.surfaceTint)
      .margin({ right: 8, bottom: 8 })
      .animation({ duration: 180, curve: Curve.EaseOut })
      .onClick(action)
  }

  @Builder buildDialogSlider(title: string, valueLabel: string, value: number, min: number, max: number, step: number, action: (value: number) => void) {
    Column() {
      Row() {
        Text(title)
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        Blank()
        Text(valueLabel)
          .fontSize(12)
          .fontColor(ControlCenterTheme.accent)
          .fontWeight(FontWeight.Bold)
      }
      .width('100%')
      Slider({ value: value, min: min, max: max, step: step, style: SliderStyle.OutSet })
        .width('100%')
        .margin({ top: 10 })
        .blockColor(ControlCenterTheme.accent)
        .trackColor('#D9E2EA')
        .selectedColor(ControlCenterTheme.accent)
        .onChange((nextValue: number) => action(Math.round(nextValue)))
    }
    .width('100%')
    .margin({ top: 12 })
  }

  @Builder buildPreviewCard() {
    Column() {
      SectionTitle({
        title: '规则摘要',
        subtitle: '确认触发条件和执行动作',
        trailing: '预览'
      })
      Text('如果 ' + this.previewCondition())
        .fontSize(13)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ top: 12 })
      Text('则 ' + this.previewAction())
        .fontSize(13)
        .fontColor(ControlCenterTheme.textPrimary)
        .margin({ top: 6 })
    }
    .width('100%')
    .padding(16)
    .borderRadius(ControlCenterTheme.radiusCard)
    .backgroundColor(ControlCenterTheme.surfaceTint)
    .margin({ top: 16 })
  }

  @Builder buildDialog() {
    Column() {
      Scroll() {
        Column() {
          Row() {
            Text('创建自动化规则')
              .fontSize(18)
              .fontWeight(FontWeight.Bold)
              .fontColor(ControlCenterTheme.textPrimary)
            Blank()
            Text('关闭')
              .fontSize(12)
              .fontWeight(FontWeight.Bold)
              .fontColor(ControlCenterTheme.textSecondary)
              .onClick(() => { this.dlg = false })
          }
          .width('100%')

          Text('把触发器、条件和执行动作串成可读规则。')
            .fontSize(12)
            .fontColor(ControlCenterTheme.textSecondary)
            .width('100%')
            .margin({ top: 6 })

          TextInput({ text: this.nm, placeholder: '例如：客厅高温自动开空调' })
            .height(48)
            .width('100%')
            .borderRadius(16)
            .backgroundColor(ControlCenterTheme.surfaceTint)
            .fontSize(15)
            .padding({ left: 14, right: 14 })
            .margin({ top: 16 })
            .onChange((value: string) => { this.nm = value })

          this.buildPreviewCard()

          Column() {
            SectionTitle({ title: '1. 选择触发器', subtitle: '选择哪个房间、哪类传感器负责触发' })
            Flex({ wrap: FlexWrap.Wrap }) {
              ForEach(this.ruleOptions.triggers, (trigger: RuleTriggerOption) => {
                this.buildChoiceChip(this.triggerLabel(trigger.value) + ' · ' + trigger.room_name, 0, trigger.value + '|' + trigger.field, () => this.pickTrigger(trigger.value, trigger.field))
              }, (trigger: RuleTriggerOption) => trigger.value + '-' + trigger.room_name + '-' + trigger.field)
            }
            .width('100%')
            .margin({ top: 12 })
          }
          .width('100%')
          .margin({ top: 18 })

          Column() {
            SectionTitle({ title: '2. 设置判断条件', subtitle: '运算符和阈值用更轻量的方式选择' })
            Scroll() {
              Row() {
                ForEach(this.availableOperators(), (operator: RuleOperatorOption) => {
                  this.buildChoiceChip(this.operatorLabel(operator.value), 1, operator.value, () => { this.op = operator.value })
                }, (operator: RuleOperatorOption) => operator.value)
              }
            }
            .scrollable(ScrollDirection.Horizontal)
            .scrollBar(BarState.Off)
            .width('100%')
            .margin({ top: 12 })

            if (this.tr !== 'pir_sensor') {
              TextInput({ text: this.vl, placeholder: '输入阈值，例如 28' })
                .height(46)
                .width('100%')
                .borderRadius(16)
                .backgroundColor(ControlCenterTheme.surfaceTint)
                .fontSize(14)
                .padding({ left: 14, right: 14 })
                .type(InputType.Number)
                .margin({ top: 12 })
                .onChange((value: string) => { this.vl = value })
            } else {
              Row() {
                this.buildChoiceChip('检测到活动', 2, 'true', () => { this.vl = 'true' })
                this.buildChoiceChip('区域空闲', 2, 'false', () => { this.vl = 'false' })
              }
              .width('100%')
              .margin({ top: 12 })
            }
          }
          .width('100%')
          .margin({ top: 18 })

          Column() {
            SectionTitle({ title: '3. 选择执行设备', subtitle: '让动作设备和房间信息更容易阅读' })
            Flex({ wrap: FlexWrap.Wrap }) {
              ForEach(this.ruleOptions.targets, (target: RuleTargetOption) => {
                this.buildChoiceChip((/[\u4e00-\u9fff]/.test(target.label) ? target.label : this.deviceTypeLabel(target.type)) + ' · ' + target.room_name, 3, target.device_id.toString(), () => this.pickTarget(target))
              }, (target: RuleTargetOption) => target.device_id.toString())
            }
            .width('100%')
            .margin({ top: 12 })
          }
          .width('100%')
          .margin({ top: 18 })

          Column() {
            SectionTitle({ title: '4. 选择执行动作', subtitle: '先选动作，再决定是否需要参数' })
            Scroll() {
              Row() {
                ForEach(this.availableActions(), (action: string) => {
                  this.buildChoiceChip(this.actionLabel(action), 4, action, () => { this.an = action })
                }, (action: string) => action)
              }
            }
            .scrollable(ScrollDirection.Horizontal)
            .scrollBar(BarState.Off)
            .width('100%')
            .margin({ top: 12 })
          }
          .width('100%')
          .margin({ top: 18 })

          if (this.showParams()) {
            Column() {
              SectionTitle({ title: '5. 细化参数', subtitle: '仅在需要设置值时显示参数控件' })
              if (this.targetType === 'light') {
                this.buildDialogSlider('亮度', this.brightnessValue.toString() + '%', this.brightnessValue, 1, 100, 1, (value: number) => { this.brightnessValue = value })
              } else if (this.targetType === 'ac') {
                this.buildDialogSlider('温度', this.tempValue.toString() + '°C', this.tempValue, 16, 30, 1, (value: number) => { this.tempValue = value })
              } else if (this.targetType === 'humidifier') {
                this.buildDialogSlider('目标湿度', this.targetHumidityValue.toString() + '%', this.targetHumidityValue, 40, 80, 1, (value: number) => { this.targetHumidityValue = value })
              } else if (this.targetType === 'curtain') {
                StatusBanner({ message: '窗帘将打开到最大位置', detail: '创建后可随时停用规则', tone: 'info' })
                  .margin({ top: 12 })
              }
            }
            .width('100%')
            .margin({ top: 18 })
          }

          Row() {
            Button('取消')
              .type(ButtonType.Capsule)
              .layoutWeight(1)
              .height(46)
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .backgroundColor(ControlCenterTheme.surfaceTint)
              .fontColor(ControlCenterTheme.textSecondary)
              .borderRadius(16)
              .onClick(() => { this.dlg = false })
            Blank().width(10)
            Button('创建规则')
              .type(ButtonType.Capsule)
              .layoutWeight(1)
              .height(46)
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .backgroundColor(ControlCenterTheme.accent)
              .fontColor('#FFFFFF')
              .borderRadius(16)
              .onClick(() => this.dC())
          }
          .width('100%')
          .margin({ top: 22 })
        }
        .width('100%')
        .padding(20)
        .borderRadius(ControlCenterTheme.radiusHero)
        .backgroundColor(ControlCenterTheme.surface)
      }
      .width('92%')
      .height('88%')
      .scrollBar(BarState.Off)
      .shadow({ radius: 24, color: ControlCenterTheme.shadowStrong, offsetY: 12 })
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(ControlCenterTheme.overlay)
  }

  @Builder buildDeleteConfirm() {
    Column() {
      Column() {
        Text('删除自动化规则')
          .fontSize(ControlCenterTheme.sectionTitleSize)
          .fontWeight(FontWeight.Bold)
          .fontColor(ControlCenterTheme.textPrimary)
        Text('确定删除“' + this.deleteTargetName + '”吗？此操作无法撤销。')
          .fontSize(ControlCenterTheme.bodySize)
          .fontColor(ControlCenterTheme.textSecondary)
          .margin({ top: 10 })
        Row() {
          Button('取消')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(ControlCenterTheme.bodySize)
            .fontColor(ControlCenterTheme.textPrimary)
            .backgroundColor(ControlCenterTheme.surfaceMuted)
            .borderRadius(ControlCenterTheme.radiusInner)
            .onClick(() => {
              this.deleteTargetId = -1
              this.deleteTargetName = ''
            })
          Blank().width(10)
          Button('确认删除')
            .layoutWeight(1)
            .height(ControlCenterTheme.tapTarget)
            .fontSize(ControlCenterTheme.bodySize)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
            .backgroundColor(ControlCenterTheme.danger)
            .borderRadius(ControlCenterTheme.radiusInner)
            .onClick(() => this.confirmDelete())
        }
        .width('100%')
        .margin({ top: 18 })
      }
      .width('86%')
      .padding(20)
      .borderRadius(ControlCenterTheme.radiusCard)
      .backgroundColor(ControlCenterTheme.surface)
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .alignItems(HorizontalAlign.Center)
    .backgroundColor(ControlCenterTheme.overlay)
  }
}
