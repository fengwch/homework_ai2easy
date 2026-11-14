package pdf

import (
	"fmt"
	"image"
	"image/draw"
	"image/jpeg"
	"image/png"
	"math"
	"os"
	"path/filepath"

	"github.com/signintech/gopdf"
)

// BuildFromImage 将一张图片（PNG/JPEG）生成 PDF：宽度适配页宽，过高则按 A4 高度分页
func BuildFromImage(imagePath string) ([]byte, error) {
	f, err := os.Open(imagePath)
	if err != nil {
		return nil, fmt.Errorf("open image: %w", err)
	}
	defer f.Close()
	img, format, err := image.Decode(f)
	if err != nil {
		return nil, fmt.Errorf("decode image: %w", err)
	}
	bounds := img.Bounds()
	w := bounds.Dx()
	h := bounds.Dy()
	if w <= 0 || h <= 0 {
		return nil, fmt.Errorf("invalid image size")
	}

	scale := pageWidth / float64(w)
	scaledHeight := float64(h) * scale
	numPages := int(math.Ceil(scaledHeight / pageHeight))
	if numPages < 1 {
		numPages = 1
	}

	pdf := &gopdf.GoPdf{}
	pdf.Start(gopdf.Config{PageSize: gopdf.Rect{W: pageWidth, H: pageHeight}})

	// 转为 RGBA 便于裁剪
	rgba := image.NewRGBA(bounds)
	draw.Draw(rgba, bounds, img, bounds.Min, draw.Src)

	tmpDir := os.TempDir()
	var segPaths []string
	defer func() {
		for _, p := range segPaths {
			_ = os.Remove(p)
		}
	}()

	for i := 0; i < numPages; i++ {
		y0 := int(float64(i) * pageHeight / scale)
		pageH := int(math.Ceil(pageHeight / scale))
		if y0+pageH > h {
			pageH = h - y0
		}
		if pageH <= 0 {
			break
		}
		cropRect := image.Rect(0, y0, w, y0+pageH)
		segment := image.NewRGBA(cropRect)
		draw.Draw(segment, segment.Bounds(), rgba, image.Pt(0, y0), draw.Src)

		segPath := filepath.Join(tmpDir, fmt.Sprintf("pdf-seg-%d.%s", i, extForFormat(format)))
		segPaths = append(segPaths, segPath)
		segFile, err := os.Create(segPath)
		if err != nil {
			return nil, fmt.Errorf("create segment temp: %w", err)
		}
		if format == "png" {
			err = png.Encode(segFile, segment)
		} else {
			err = jpeg.Encode(segFile, segment, &jpeg.Options{Quality: 90})
		}
		_ = segFile.Close()
		if err != nil {
			return nil, fmt.Errorf("encode segment: %w", err)
		}

		pdf.AddPage()
		segHeightPt := float64(pageH) * scale
		if segHeightPt > pageHeight {
			segHeightPt = pageHeight
		}
		err = pdf.Image(segPath, 0, 0, &gopdf.Rect{W: pageWidth, H: segHeightPt})
		if err != nil {
			return nil, fmt.Errorf("add image to pdf: %w", err)
		}
	}

	outPath := filepath.Join(tmpDir, "export-from-image.pdf")
	_ = os.Remove(outPath)
	defer os.Remove(outPath)
	if err := pdf.WritePdf(outPath); err != nil {
		return nil, err
	}
	return os.ReadFile(outPath)
}

func extForFormat(format string) string {
	switch format {
	case "png":
		return "png"
	case "jpeg", "jpg":
		return "jpg"
	default:
		return "png"
	}
}
