@Component
export struct SmartHomeLogo {
  @Prop logoSize: number = 160

  private middleSize(): number {
    return Math.floor(this.logoSize * 0.82)
  }

  private innerSize(): number {
    return Math.floor(this.logoSize * 0.7)
  }

  private iconSize(): number {
    return Math.floor(this.logoSize * 0.32)
  }

  build() {
    Stack({ alignContent: Alignment.Center }) {
      Circle()
        .width(this.logoSize).height(this.logoSize)
        .fill('#07C16008')
        .strokeWidth(1.5)
        .stroke('#07C16015')

      Circle()
        .width(this.middleSize()).height(this.middleSize())
        .fill('#07C16012')

      Circle()
        .width(this.innerSize()).height(this.innerSize())
        .fill('#FFFFFF')
        .shadow({ radius: 8, color: '#07C16015', offsetY: 1 })

      Text('\uD83C\uDFE0')
        .fontSize(this.iconSize())
    }
    .width(this.logoSize).height(this.logoSize)
  }
}

@Component
export struct SmartHomeLogoSmall {
  build() {
    Stack({ alignContent: Alignment.Center }) {
      Circle()
        .width(34).height(34)
        .fill('#07C16012')
      Text('\uD83C\uDFE0')
        .fontSize(18)
    }
    .width(34).height(34)
  }
}
