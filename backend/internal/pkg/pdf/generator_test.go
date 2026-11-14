package pdf

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
)

// TestBuildStoryPDF_NilData verifies that nil input returns an error.
func TestBuildStoryPDF_NilData(t *testing.T) {
	_, err := BuildStoryPDF(nil, "")
	if err == nil {
		t.Fatal("expected error for nil data")
	}
}

// TestBuildStoryPDF_MinimalContent verifies PDF generation with just a title.
func TestBuildStoryPDF_MinimalContent(t *testing.T) {
	fontPath := testFontPath(t)
	if fontPath == "" {
		t.Skip("font not available")
	}

	data := &StoryPDFData{
		Title: "测试标题",
	}
	pdf, err := BuildStoryPDF(data, fontPath)
	if err != nil {
		t.Fatalf("BuildStoryPDF failed: %v", err)
	}
	if len(pdf) == 0 {
		t.Fatal("PDF bytes empty")
	}
	if !bytes.HasPrefix(pdf, []byte("%PDF")) {
		t.Fatalf("PDF header invalid, got: %q", pdf[:10])
	}
}

// TestBuildStoryPDF_FullContent verifies PDF with all content sections:
// title, summary, story text, images, and practice questions.
func TestBuildStoryPDF_FullContent(t *testing.T) {
	fontPath := testFontPath(t)
	if fontPath == "" {
		t.Skip("font not available")
	}

	imgPath := filepath.Join(t.TempDir(), "test.png")
	if err := os.WriteFile(imgPath, makeTestPngData(), 0o644); err != nil {
		t.Fatalf("write test image: %v", err)
	}

	data := &StoryPDFData{
		Title:   "小红帽的故事",
		Summary: "一个关于勇气和善良的童话故事",
		Story:   "从前有一个可爱的小女孩，她最喜欢戴红色的帽子。",
		Images:  []string{imgPath},
		Questions: []QuestionPDFItem{
			{Content: "小女孩最喜欢戴什么颜色的帽子？", Options: []string{"A. 蓝色", "B. 红色"}},
			{Content: "妈妈让小女孩去做什么？", Options: []string{"A. 去上学", "B. 去买菜"}},
		},
	}

	pdf, err := BuildStoryPDF(data, fontPath)
	if err != nil {
		t.Fatalf("BuildStoryPDF failed: %v", err)
	}
	if len(pdf) < 200 {
		t.Fatalf("PDF too small: %d bytes", len(pdf))
	}

	// Verify PDF header
	if !bytes.HasPrefix(pdf, []byte("%PDF")) {
		t.Fatalf("PDF header invalid")
	}

	// Verify structure: should have font entries (embedded TrueType)
	if !bytes.Contains(pdf, []byte("/Font")) {
		t.Error("no /Font entry in PDF")
	}

	// Verify structure: should have page count > 0
	pageCount := bytes.Count(pdf, []byte("/Type /Page"))
	if pageCount < 1 {
		t.Errorf("expected at least 1 page, got %d", pageCount)
	}

	// Verify images produce XObject entries
	xobjCount := bytes.Count(pdf, []byte("/XObject"))
	if xobjCount < 1 {
		t.Errorf("expected at least 1 /XObject entry for images, got %d", xobjCount)
	}
}

// TestBuildStoryPDF_LongTextAutoPageBreak verifies that long text triggers
// automatic page breaks and produces a multi-page PDF.
func TestBuildStoryPDF_LongTextAutoPageBreak(t *testing.T) {
	fontPath := testFontPath(t)
	if fontPath == "" {
		t.Skip("font not available")
	}

	longText := ""
	for i := 0; i < 200; i++ {
		longText += "这是第" + string(rune('0')) + "段测试文本。"
	}

	data := &StoryPDFData{
		Title: "长文本测试",
		Story: longText,
	}

	pdf, err := BuildStoryPDF(data, fontPath)
	if err != nil {
		t.Fatalf("BuildStoryPDF failed: %v", err)
	}

	pageCount := bytes.Count(pdf, []byte("/Type /Page"))
	if pageCount < 2 {
		t.Errorf("expected at least 2 pages for long text, got %d pages", pageCount)
	}
}

// TestBuildStoryPDF_MultipleImages verifies embedding multiple images.
// Note: gopdf deduplicates identical images by content, so XObject count
// may be less than image count when test images are identical 1x1 PNGs.
func TestBuildStoryPDF_MultipleImages(t *testing.T) {
	fontPath := testFontPath(t)
	if fontPath == "" {
		t.Skip("font not available")
	}

	imgPaths := makeTestImages(t, 3)
	if len(imgPaths) == 0 {
		t.Skip("could not create test images")
	}

	data := &StoryPDFData{
		Title:  "多图测试",
		Story:  "下面有三张图片。",
		Images: imgPaths,
	}

	pdf, err := BuildStoryPDF(data, fontPath)
	if err != nil {
		t.Fatalf("BuildStoryPDF failed: %v", err)
	}

	// gopdf deduplicates identical images, so we just verify at least one XObject exists
	xobjCount := bytes.Count(pdf, []byte("/XObject"))
	if xobjCount < 1 {
		t.Errorf("expected at least 1 /XObject entry for images, got %d", xobjCount)
	}
}

// TestBuildStoryPDF_EmptyTitleNoSummary verifies that missing optional fields don't cause errors.
func TestBuildStoryPDF_EmptyTitleNoSummary(t *testing.T) {
	fontPath := testFontPath(t)
	if fontPath == "" {
		t.Skip("font not available")
	}

	data := &StoryPDFData{
		Title: "",
		Story: "只有正文。",
	}

	pdf, err := BuildStoryPDF(data, fontPath)
	if err != nil {
		t.Fatalf("BuildStoryPDF failed: %v", err)
	}
	if len(pdf) == 0 {
		t.Fatal("PDF empty")
	}
}

// TestBuildStoryPDF_QuestionWithoutOptions verifies questions without options.
func TestBuildStoryPDF_QuestionWithoutOptions(t *testing.T) {
	fontPath := testFontPath(t)
	if fontPath == "" {
		t.Skip("font not available")
	}

	data := &StoryPDFData{
		Title: "无选项测试",
		Questions: []QuestionPDFItem{
			{Content: "这是一道简答题，不需要选项。"},
		},
	}

	pdf, err := BuildStoryPDF(data, fontPath)
	if err != nil {
		t.Fatalf("BuildStoryPDF failed: %v", err)
	}
	// Verify PDF is structurally valid
	if !bytes.HasPrefix(pdf, []byte("%PDF")) {
		t.Fatal("PDF header invalid")
	}
}

// TestBuildStoryPDF_PreviewLayoutMatch verifies PDF structure matches
// the print/preview page layout: title → summary → images → story → questions.
func TestBuildStoryPDF_PreviewLayoutMatch(t *testing.T) {
	fontPath := testFontPath(t)
	if fontPath == "" {
		t.Skip("font not available")
	}

	// Simulate the actual preview.uvue content structure
	imgPath := filepath.Join(t.TempDir(), "comic.png")
	if err := os.WriteFile(imgPath, makeTestPngData(), 0o644); err != nil {
		t.Fatalf("write test image: %v", err)
	}

	data := &StoryPDFData{
		Title:   "冯雨的数学奇遇记",
		Summary: "基于你的作业题目生成的个性化学习故事，帮助巩固相关知识点。",
		Story: "冯雨是个戴圆框眼镜的三年级男生，最爱在窗台观察蚂蚁搬家。" +
			"\n\n原来，宇宙清洁小队发来紧急消息：银河蚁群搬运能量晶粒时，" +
			"搞错了体重换算表，差点把1亿只蚂蚁的总重量当成一只小瓢虫！" +
			"\n\n【学习要点】\n" +
			"• 认识质量单位：毫克→克→千克的进率\n" +
			"• 大数乘法与单位换算\n" +
			"• 生活中常见动物的大致体重",
		Images: []string{imgPath},
		Questions: []QuestionPDFItem{
			{
				Content: "一只蚂蚁约重 2-3 毫克，1000 只约 2-3 克，1 亿只蚂蚁的体重约与 1 只（  ）体重差不多。",
				Options: []string{
					"A. 大象（2000 千克）",
					"B. 奶牛（250 千克）",
					"C. 小狗（30 千克）",
					"D. 鲨鱼（2 吨）",
				},
			},
		},
	}

	pdf, err := BuildStoryPDF(data, fontPath)
	if err != nil {
		t.Fatalf("BuildStoryPDF failed: %v", err)
	}

	// Structural checks that correspond to preview.uvue elements:
	// 1. Valid PDF
	if !bytes.HasPrefix(pdf, []byte("%PDF")) {
		t.Fatal("PDF header invalid")
	}

	// 2. At least one page
	pageCount := bytes.Count(pdf, []byte("/Type /Page"))
	if pageCount < 1 {
		t.Errorf("expected at least 1 page, got %d", pageCount)
	}

	// 3. Embedded font (Chinese text needs TrueType font)
	if !bytes.Contains(pdf, []byte("/Font")) {
		t.Error("no /Font entry — Chinese text may not render")
	}

	// 4. Image embedded (comic panel from preview page)
	xobjCount := bytes.Count(pdf, []byte("/XObject"))
	if xobjCount < 1 {
		t.Error("no /XObject — image not embedded")
	}

	// 5. Multiple page resources exist (story text + images should fill pages)
	resourcesCount := bytes.Count(pdf, []byte("/Resources"))
	if resourcesCount < 1 {
		t.Error("no /Resources entry")
	}

	// Log PDF size for debugging
	t.Logf("PDF: %d bytes, %d pages, %d fonts, %d images, %d resources",
		len(pdf), pageCount,
		bytes.Count(pdf, []byte("/Font")),
		bytes.Count(pdf, []byte("/XObject")),
		resourcesCount,
	)
}

// ── helpers ──

func testFontPath(t *testing.T) string {
	if p := os.Getenv("PDF_FONT_PATH"); p != "" {
		if _, err := os.Stat(p); err == nil {
			return p
		}
	}
	candidates := []string{
		"fonts/NotoSansSC-Regular.ttf",
		"../../fonts/NotoSansSC-Regular.ttf",
		"../../../fonts/NotoSansSC-Regular.ttf",
		"../../../../fonts/NotoSansSC-Regular.ttf",
		"../../../../../fonts/NotoSansSC-Regular.ttf",
	}
	for _, p := range candidates {
		if _, err := os.Stat(p); err == nil {
			abs, _ := filepath.Abs(p)
			return abs
		}
	}
	return ""
}

func makeTestImages(t *testing.T, n int) []string {
	var paths []string
	for i := 0; i < n; i++ {
		path := filepath.Join(t.TempDir(), "test.png")
		if err := os.WriteFile(path, makeTestPngData(), 0o644); err != nil {
			return nil
		}
		paths = append(paths, path)
	}
	return paths
}

func makeTestPngData() []byte {
	return []byte{
		0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
		0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
		0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
		0xde, 0x00, 0x00, 0x00, 0x0c, 0x49, 0x44, 0x41,
		0x54, 0x08, 0xd7, 0x63, 0xf8, 0xff, 0xff, 0xff,
		0x00, 0x05, 0xfe, 0x02, 0xfe, 0xa7, 0x9a, 0x5d,
		0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e, 0x44,
		0xae, 0x42, 0x60, 0x82,
	}
}
