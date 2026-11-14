package pdf

import (
	"bytes"
	"fmt"
	"image"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/google/uuid"
	"github.com/signintech/gopdf"
)

// StoryPDFData 用于生成学习材料 PDF 的结构化数据。
// 字段对应前端 pages/print/preview.uvue 的展示结构。
type StoryPDFData struct {
	Title     string
	Summary   string
	Story     string
	Images    []string // 本地文件路径（PNG/JPEG），非 URL
	Questions []QuestionPDFItem
}

// QuestionPDFItem 练习题项。
type QuestionPDFItem struct {
	Content string
	Options []string
}

const (
	a4Width  = 595.28
	a4Height = 841.89
	// Compat aliases for image_to_pdf.go
	pageWidth  = a4Width
	pageHeight = a4Height
)

// 排版常量：与 preview.uvue 页面对应的视觉层次（单位均为 pt，gopdf 默认单位）。
const (
	pdfMargin    = 56.7  // 20mm ≈ 56.7pt，对应前端 ~32rpx padding
	pdfTextWidth = 481.8 // A4宽 - 2*margin
	pdfTitleSize = 18.0  // 标题字号
	pdfBodySize  = 13.0  // 正文字号
	pdfQLabelSz  = 11.0  // 题号字号
	pdfQBodySz   = 12.0  // 题目正文字号
	pdfQOptSz    = 10.0  // 选项字号

	lineRatio  = 1.65  // 行高 = 字号 × lineRatio（前端 line-height: 1.8，PDF 略紧凑）
	paraGap    = 10.0  // 段落间距 pt
	imgMaxH    = 160.0 // 插图最大高度 pt（约 56mm），缩小以和文字共存一页
	sectionGap = 16.0  // 区块间距 pt（标题↔摘要↔图片↔正文之间）
	qGap       = 12.0  // 题目之间间距 pt
)

// BuildStoryPDF 根据结构化数据生成 PDF 字节。
// 排版顺序与 preview.uvue 一致：标题 → 摘要 → 配图 → 正文 → 练习题。
// 自动分页，图片按页宽等比缩放。
func BuildStoryPDF(data *StoryPDFData, fontPath string) ([]byte, error) {
	if data == nil {
		return nil, fmt.Errorf("story pdf data is nil")
	}
	if fontPath == "" {
		return nil, fmt.Errorf("font path is empty")
	}
	if _, err := os.Stat(fontPath); err != nil {
		return nil, fmt.Errorf("font file not found: %s", fontPath)
	}

	pdf := &gopdf.GoPdf{}
	pdf.Start(gopdf.Config{PageSize: gopdf.Rect{W: a4Width, H: a4Height}})
	pdf.AddPage()

	if err := pdf.AddTTFFont("sans", fontPath); err != nil {
		return nil, fmt.Errorf("add ttf font: %w", err)
	}

	w := newWriter(pdf, fontPath)

	// 标题
	if data.Title != "" {
		w.writeStyled(data.Title, pdfTitleSize, true)
		w.y += sectionGap
	}

	// 摘要
	if data.Summary != "" {
		w.writeStyled(data.Summary, pdfBodySize-1, false)
		w.y += sectionGap
	}

	// 配图：占满当前页剩余空间（标题和摘要下方），正文从第二页开始
	for _, imgPath := range data.Images {
		if imgPath == "" {
			continue
		}
		// 计算当前页面剩余可用高度（扣除底部边距）
		remainingH := a4Height - w.y - pdfMargin
		w.drawImageFill(imgPath, remainingH)
	}

	// 正文（图片已占满第一页，正文自然从第二页开始）
	if data.Story != "" {
		w.writeStyled(data.Story, pdfBodySize, false)
		w.y += sectionGap
	}

	// 练习题
	if len(data.Questions) > 0 {
		w.y += sectionGap
		for i, q := range data.Questions {
			label := fmt.Sprintf("第%d题", i+1)
			w.writeStyled(label, pdfQLabelSz, true)
			w.writeStyled(q.Content, pdfQBodySz, false)
			for _, opt := range q.Options {
				w.writeStyled("  "+opt, pdfQOptSz, false)
			}
			if i < len(data.Questions)-1 {
				w.y += qGap
			}
		}
	}

	var buf bytes.Buffer
	if err := pdf.Write(&buf); err != nil {
		return nil, fmt.Errorf("write pdf: %w", err)
	}
	return buf.Bytes(), nil
}

// pdfWriter 封装 gopdf 的文本写入与分页逻辑。
type pdfWriter struct {
	pdf      *gopdf.GoPdf
	fontPath string
	y        float64
}

func newWriter(pdf *gopdf.GoPdf, fontPath string) *pdfWriter {
	return &pdfWriter{
		pdf:      pdf,
		fontPath: fontPath,
		y:        pdfMargin,
	}
}

// writeStyled 写入一段文本，自动换行、自动分页，段落之间留空。
// bold 参数仅在字体存在粗体变体时生效，否则使用常规字体（字体仅注册了 Regular）。
func (w *pdfWriter) writeStyled(text string, fontSize float64, bold bool) {
	// gopdf 只注册了 sans Regular，不区分 B/I 变体。
	// 加粗效果通过加大 0.5pt 字号模拟，保持视觉层次。
	displaySize := fontSize
	if bold {
		displaySize += 0.5
	}
	w.pdf.SetFont("sans", "", displaySize)

	maxW := pdfTextWidth
	lh := fontSize * lineRatio // 根据字号动态计算行高，避免字重叠

	paras := splitParagraphs(text)
	for i, para := range paras {
		if len(para) == 0 {
			// 空段落 = 段间距（跳过当前行高，只留 paraGap）
			w.y += paraGap
			continue
		}
		subLines := w.splitLine(para, maxW, displaySize)
		for _, line := range subLines {
			w.ensureSpace(lh)
			w.pdf.SetXY(pdfMargin, w.y)
			w.pdf.Cell(nil, line)
			w.y += lh
		}
		// 非最后一段时追加段落间距
		if i < len(paras)-1 {
			w.y += paraGap
		}
	}
}

// splitLine 根据字体宽度将文本切分为不超过 maxW 的多行。
func (w *pdfWriter) splitLine(text string, maxW, fontSize float64) []string {
	if len(text) == 0 {
		return []string{""}
	}

	w.pdf.SetFont("sans", "", fontSize)
	runes := []rune(text)
	var lines []string
	var cur []rune

	for _, r := range runes {
		cur = append(cur, r)
		s := string(cur)
		tw, err := w.pdf.MeasureTextWidth(s)
		if err != nil {
			tw = float64(len(cur)) * fontSize * 0.6 // fallback estimation
		}
		if tw > maxW {
			if len(cur) > 1 {
				lines = append(lines, string(cur[:len(cur)-1]))
				cur = []rune{r}
			} else {
				lines = append(lines, string(cur))
				cur = nil
			}
		}
	}
	if len(cur) > 0 {
		lines = append(lines, string(cur))
	}
	if len(lines) == 0 {
		lines = []string{""}
	}
	return lines
}

// ensureSpace 检查剩余空间是否足够，不足则分页。
func (w *pdfWriter) ensureSpace(need float64) {
	if w.y+need > a4Height-pdfMargin {
		w.pdf.AddPage()
		w.y = pdfMargin
	}
}

// drawImage 将本地图片嵌入 PDF，放在文字后面，高度不超 imgMaxH，宽度按比例，居中显示。
func (w *pdfWriter) drawImage(path string) {
	if _, err := os.Stat(path); err != nil {
		return
	}

	f, err := os.Open(path)
	if err != nil {
		return
	}
	img, _, err := image.Decode(f)
	_ = f.Close()
	if err != nil {
		return
	}
	bounds := img.Bounds()
	imgW := float64(bounds.Dx())
	imgH := float64(bounds.Dy())
	if imgW <= 0 || imgH <= 0 {
		return
	}

	// 先按页宽等比缩放
	scale := pdfTextWidth / imgW
	displayW := pdfTextWidth
	displayH := imgH * scale

	// 若高度超过上限，按高度等比压缩（不放大小图）
	if displayH > imgMaxH {
		scale = imgMaxH / imgH
		displayH = imgMaxH
		displayW = imgW * scale
	}

	w.ensureSpace(displayH + sectionGap)

	// 居中绘制
	x := pdfMargin + (pdfTextWidth-displayW)/2
	w.pdf.Image(path, x, w.y, &gopdf.Rect{
		W: displayW,
		H: displayH,
	})
	w.y += displayH + sectionGap
}

// drawImageFill 将图片按指定高度等比缩放并嵌入，宽度按比例，居中显示。
// 用于让图片占满当前页剩余空间（标题和摘要下方）。
func (w *pdfWriter) drawImageFill(path string, maxH float64) {
	if _, err := os.Stat(path); err != nil {
		return
	}

	f, err := os.Open(path)
	if err != nil {
		return
	}
	img, _, err := image.Decode(f)
	_ = f.Close()
	if err != nil {
		return
	}
	bounds := img.Bounds()
	imgW := float64(bounds.Dx())
	imgH := float64(bounds.Dy())
	if imgW <= 0 || imgH <= 0 {
		return
	}

	// 按目标高度等比缩放
	scale := maxH / imgH
	displayH := maxH
	displayW := imgW * scale

	// 若宽度超出文本区域，按页宽等比重新计算（保持比例）
	if displayW > pdfTextWidth {
		scale = pdfTextWidth / imgW
		displayW = pdfTextWidth
		displayH = imgH * scale
	}

	// 居中绘制
	x := pdfMargin + (pdfTextWidth-displayW)/2
	w.pdf.Image(path, x, w.y, &gopdf.Rect{
		W: displayW,
		H: displayH,
	})
	w.y += displayH + sectionGap
}

func splitParagraphs(text string) []string {
	var paras []string
	var cur []rune
	for _, r := range text {
		if r == '\n' || r == '\r' {
			if len(cur) > 0 {
				paras = append(paras, string(cur))
				cur = nil
			}
		} else {
			cur = append(cur, r)
		}
	}
	if len(cur) > 0 {
		paras = append(paras, string(cur))
	}
	if len(paras) == 0 {
		paras = []string{""}
	}
	return paras
}

// ResolveFontPath 导出字体查找逻辑供 server 使用。
func ResolveFontPath(configured string) string {
	if configured != "" {
		if _, err := os.Stat(configured); err == nil {
			return configured
		}
	}
	candidates := []string{
		"fonts/NotoSansSC-Regular.ttf",
		"config/fonts/NotoSansSC-Regular.ttf",
		"internal/pkg/pdf/fonts/NotoSansSC-Regular.ttf",
	}
	for _, p := range candidates {
		if _, err := os.Stat(p); err == nil {
			return p
		}
		abs, _ := filepath.Abs(p)
		if _, err := os.Stat(abs); err == nil {
			return abs
		}
	}
	return ""
}

// DownloadImageToTemp 从 URL 下载图片到临时文件，返回路径和清理函数。
func DownloadImageToTemp(imgURL string) (imgPath string, cleanup func(), err error) {
	cleanup = func() {}

	resp, err := http.Get(imgURL)
	if err != nil {
		return "", cleanup, fmt.Errorf("download image: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return "", cleanup, fmt.Errorf("download image: status %d", resp.StatusCode)
	}

	ext := ".png"
	ct := resp.Header.Get("Content-Type")
	if strings.Contains(ct, "jpeg") || strings.Contains(ct, "jpg") {
		ext = ".jpg"
	}

	tmpPath := filepath.Join(os.TempDir(), "story-pdf-img-"+uuid.New().String()+ext)
	dst, err := os.Create(tmpPath)
	if err != nil {
		return "", cleanup, fmt.Errorf("create temp: %w", err)
	}
	_, err = io.Copy(dst, resp.Body)
	_ = dst.Close()
	if err != nil {
		_ = os.Remove(tmpPath)
		return "", cleanup, fmt.Errorf("save temp: %w", err)
	}
	cleanup = func() { _ = os.Remove(tmpPath) }
	return tmpPath, cleanup, nil
}
