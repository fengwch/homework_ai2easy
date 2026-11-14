/**
 * 前端根据当前打印预览的数据生成 PDF，不依赖后端。
 * 使用 jspdf，布局与页面展示一致（标题、摘要、配图、正文、练习题）。
 */
// @ts-ignore - jspdf 可能无类型定义
import { jsPDF } from 'jspdf'

const PAGE_W = 210
const PAGE_H = 297
const MARGIN = 20
const TEXT_W = PAGE_W - MARGIN * 2
const LINE_HEIGHT = 6
const IMAGE_MAX_W = TEXT_W
const IMAGE_MAX_H = 120

export interface PdfContentData {
  title: string
  summary?: string
  story?: string
  imagesBase64?: string[]
  questions?: Array<{ content: string; options?: string[] }>
}

/**
 * 将学习材料数据生成为 PDF，返回 base64 字符串（不含 data:application/pdf;base64, 前缀，便于写入文件）
 */
export function buildLearningContentPdf(data: PdfContentData): Promise<string> {
  return new Promise((resolve, reject) => {
    try {
      const doc = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' })
      let y = MARGIN

      const checkPage = (needSpace: number) => {
        if (y + needSpace > PAGE_H - MARGIN) {
          doc.addPage()
          y = MARGIN
        }
      }

      const putLines = (text: string, fontSize: number, lineHeight: number = LINE_HEIGHT) => {
        doc.setFontSize(fontSize)
        const lines = doc.splitTextToSize(text, TEXT_W)
        for (let i = 0; i < lines.length; i++) {
          checkPage(lineHeight)
          doc.text(lines[i], MARGIN, y)
          y += lineHeight
        }
      }

      // 标题
      if (data.title) {
        doc.setFontSize(18)
        doc.setFont('helvetica', 'bold')
        putLines(data.title, 18, 8)
        y += 4
      }

      // 摘要
      if (data.summary) {
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(10)
        putLines(data.summary, 10, 5)
        y += 4
      }

      // 配图（与页面展示顺序一致）
      if (data.imagesBase64 && data.imagesBase64.length > 0) {
        for (let i = 0; i < data.imagesBase64.length; i++) {
          const dataUrl = data.imagesBase64[i]
          if (!dataUrl) continue
          checkPage(IMAGE_MAX_H + 8)
          try {
            const format = dataUrl.indexOf('image/png') !== -1 ? 'PNG' : 'JPEG'
            doc.addImage(dataUrl, format, MARGIN, y, IMAGE_MAX_W, IMAGE_MAX_H)
            y += IMAGE_MAX_H + 8
          } catch (_) {
            // 单张图失败可跳过
          }
        }
      }

      // 故事正文
      if (data.story) {
        doc.setFontSize(11)
        putLines(data.story, 11, 6)
        y += 8
      }

      // 练习题
      if (data.questions && data.questions.length > 0) {
        doc.setFont('helvetica', 'bold')
        doc.setFontSize(12)
        doc.text('练习题', MARGIN, y)
        y += 10
        doc.setFont('helvetica', 'normal')

        for (let i = 0; i < data.questions.length; i++) {
          const q = data.questions[i]
          checkPage(20)
          doc.setFontSize(10)
          doc.setFont('helvetica', 'bold')
          doc.text(`第${i + 1}题`, MARGIN, y)
          y += 6
          doc.setFont('helvetica', 'normal')
          putLines(q.content, 10, 5)
          if (q.options && q.options.length > 0) {
            doc.setFontSize(9)
            putLines(q.options.join('  '), 9, 5)
          }
          y += 6
        }
      }

      const dataUrl = doc.output('datauristring')
      const base64 = dataUrl.indexOf('base64,') !== -1 ? dataUrl.split('base64,')[1] : ''
      resolve(base64)
    } catch (e) {
      reject(e)
    }
  })
}
