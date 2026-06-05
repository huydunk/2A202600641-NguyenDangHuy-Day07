# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Đăng Huy — MSSV: 2A202600641
**Nhóm:** Nhóm 2
**Ngày:** 05/06/2026

---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
> Hai văn bản có cosine similarity cao nghĩa là vector embedding của chúng chỉ cùng một hướng trong không gian vector — tức là mô hình embedding đánh giá chúng có ý nghĩa tương tự nhau, bất kể độ dài hay từ ngữ cụ thể.

**Ví dụ HIGH similarity:**
- Sentence A: "CMMI giúp tổ chức cải thiện quy trình phần mềm"
- Sentence B: "Mô hình CMMI hỗ trợ nâng cao năng lực và chất lượng quy trình"
- Tại sao tương đồng: Cả hai câu đều nói về mục đích của CMMI trong việc cải thiện quy trình, dù dùng từ ngữ khác nhau.

**Ví dụ LOW similarity:**
- Sentence A: "Configuration Management kiểm soát phiên bản và baseline sản phẩm"
- Sentence B: "Hôm nay thời tiết rất đẹp và nắng"
- Tại sao khác: Một câu về kỹ thuật phần mềm, một câu về thời tiết — hoàn toàn khác chủ đề và ngữ nghĩa.

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
> Cosine similarity đo góc giữa hai vector, không bị ảnh hưởng bởi độ dài văn bản — một câu ngắn và một đoạn dài về cùng chủ đề vẫn có cosine similarity cao. Euclidean distance bị ảnh hưởng bởi magnitude của vector, nên văn bản dài hơn tự nhiên xa hơn dù cùng nghĩa.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> Phép tính: `num_chunks = ceil((10000 - 50) / (500 - 50)) = ceil(9950 / 450) = ceil(22.11) = 23`
> Đáp án: **23 chunks**

**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
> Với overlap=100: `ceil((10000 - 100) / (500 - 100)) = ceil(9900 / 400) = ceil(24.75) = 25 chunks` — nhiều hơn 2 chunks. Overlap lớn hơn giúp mỗi chunk giữ được ngữ cảnh từ chunk trước, giảm nguy cơ cắt đứt giữa một ý quan trọng — đặc biệt hữu ích khi một khái niệm trải dài qua ranh giới chunk.

---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** CMMI V2.0 — Software Process Improvement (Cải tiến quy trình phần mềm)

**Tại sao nhóm chọn domain này?**
> CMMI V2.0 là tài liệu kỹ thuật có cấu trúc phân cấp rõ ràng (View → Capability Area → Practice Area → Practice), rất phù hợp để thử nghiệm các chiến lược chunking. Domain này cũng thực tế vì nhiều tổ chức phần mềm cần tra cứu nhanh các practice và maturity level. Ngoài ra, tài liệu đủ dài (107K ký tự) để thấy rõ sự khác biệt giữa các strategy chunking.

### Data Inventory

| # | Tên tài liệu | Nguồn | Số ký tự | Metadata đã gán |
|---|--------------|-------|----------|-----------------|
| 1 | cmmi_nhom2.md | BTL nhóm 2 — chuyển từ DOCX | 107,147 | source, doc_id, chunk_index |
| 2 | python_intro.txt | Lab sample | 1,944 | source, doc_id |
| 3 | rag_system_design.md | Lab sample | 2,391 | source, doc_id |
| 4 | vector_store_notes.md | Lab sample | 2,123 | source, doc_id |
| 5 | chunking_experiment_report.md | Lab sample | 1,987 | source, doc_id |

### Metadata Schema

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho retrieval? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `"cmmi_nhom2"` | Cho phép `delete_document()` xoá đúng tài liệu; dùng filter theo nguồn |
| `source` | string | `"data/cmmi_nhom2.md"` | Biết chunk đến từ file nào khi hiển thị kết quả |
| `chunk_index` | int | `42` | Xác định vị trí chunk trong tài liệu gốc; hữu ích khi cần lấy context lân cận |
| `section` | string | `"maturity_levels"` | Filter theo chủ đề lớn — ví dụ chỉ tìm trong phần Maturity Levels |

---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên tài liệu `cmmi_nhom2.md` (107,147 ký tự):

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| cmmi_nhom2.md | FixedSizeChunker (`fixed_size`, size=400) | 306 | 399 chars | Không — cắt giữa câu/đoạn |
| cmmi_nhom2.md | SentenceChunker (`by_sentences`, max=3) | 316 | 336 chars | Một phần — giữ ranh giới câu |
| cmmi_nhom2.md | RecursiveChunker (`recursive`, size=400) | 351 | 304 chars | Tốt — giữ ranh giới đoạn/câu |

### Strategy Của Tôi

**Loại:** RecursiveChunker (chunk_size=400)

**Mô tả cách hoạt động:**
> RecursiveChunker thử chia văn bản theo các separator theo thứ tự ưu tiên: `\n\n` (đoạn văn), `\n` (dòng), `. ` (câu), ` ` (từ). Nếu một đoạn vẫn lớn hơn chunk_size sau khi chia, nó tiếp tục đệ quy với separator tiếp theo. Sau khi chia xong, các chunk nhỏ liền kề được gộp lại (greedy merge) miễn là tổng độ dài không vượt chunk_size. Cách này ưu tiên giữ nguyên cấu trúc lớn trước, chỉ chia nhỏ khi thực sự cần.

**Tại sao tôi chọn strategy này cho domain nhóm?**
> Tài liệu CMMI V2.0 có cấu trúc phân cấp rõ ràng: phần → mục → đoạn văn → câu. RecursiveChunker khai thác đúng cấu trúc này bằng cách cố gắng giữ nguyên đoạn văn hoàn chỉnh trước khi chia nhỏ hơn. Điều này đặc biệt quan trọng với tài liệu kỹ thuật như CMMI, nơi mỗi đoạn thường diễn giải một khái niệm trọn vẹn — cắt giữa đoạn sẽ mất ngữ cảnh.

**Code snippet:**
```python
chunker = RecursiveChunker(chunk_size=400)
chunks = chunker.chunk(content)
```

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| cmmi_nhom2.md | FixedSizeChunker (best baseline) | 306 | 399 chars | 3/5 queries relevant |
| cmmi_nhom2.md | **RecursiveChunker (của tôi)** | **351** | **304 chars** | **4/5 queries relevant** |

RecursiveChunker tạo ra nhiều chunk hơn nhưng nhỏ hơn và coherent hơn, giúp retrieval chính xác hơn. FixedSizeChunker đôi khi cắt giữa định nghĩa quan trọng (ví dụ Query 4 — CM) nên bỏ lỡ chunk phù hợp.

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | RecursiveChunker (size=400) | 8/10 | Giữ ngữ cảnh đoạn văn, score cao | Chunk nhỏ hơn, đôi khi thiếu context cross-paragraph |
| [Tên] | SentenceChunker (max=3) | 7/10 | Chunk dễ đọc, ranh giới tự nhiên | Size không đồng đều, yếu ở Q4 |
| [Tên] | FixedSizeChunker (size=400) | 7/10 | Số chunk ít, dễ dự đoán | Cắt giữa câu/đoạn, mất context |

**Strategy nào tốt nhất cho domain này? Tại sao?**
> RecursiveChunker phù hợp nhất với tài liệu CMMI V2.0 vì tài liệu có cấu trúc phân cấp rõ ràng với các đoạn văn mang ý nghĩa trọn vẹn. Strategy này đạt 4/5 queries relevant trong top-1 và có điểm similarity cao nhất ở 3/5 queries. Tuy nhiên, không có strategy nào là tuyệt đối — Query 1 (định nghĩa tổng quát) vẫn yếu ở cả 3 strategy vì thông tin trải rộng khắp tài liệu.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
> Dùng `re.split(r"(?<=[.!?])\s+|\.\n", text)` để tách văn bản tại ranh giới câu — lookbehind đảm bảo dấu chấm/hỏi/than được giữ ở cuối câu trước. Sau khi tách, lọc bỏ chuỗi rỗng rồi nhóm các câu lại thành batch theo `max_sentences_per_chunk`, join bằng khoảng trắng và strip whitespace thừa.

**`RecursiveChunker.chunk` / `_split`** — approach:
> `chunk()` chỉ gọi `_split(text, self.separators)`. `_split()` có hai base case: nếu text đã ngắn hơn chunk_size thì trả về ngay; nếu hết separator thì cắt cứng tại chunk_size. Trường hợp đệ quy: lấy separator đầu tiên, split text, gọi đệ quy trên từng phần với phần separator còn lại. Sau đó greedy merge các chunk liền kề nhỏ lại với nhau, tái thêm separator vào giữa, miễn là tổng không vượt chunk_size.

### EmbeddingStore

**`add_documents` + `search`** — approach:
> `_make_record()` embed nội dung doc bằng `embedding_fn`, lưu thành dict gồm `id` (auto-increment), `content`, `embedding`, và `metadata` (kết hợp `doc.id` vào key `doc_id`). `add_documents()` gọi `_make_record()` cho từng doc và append vào `self._store`. `search()` delegate sang `_search_records()` — hàm này embed query, tính dot product với từng record, sort giảm dần, trả về top-k với key `score` được thêm vào mỗi kết quả.

**`search_with_filter` + `delete_document`** — approach:
> `search_with_filter()` filter trước: giữ lại các record có metadata khớp tất cả key-value trong `metadata_filter`, rồi mới gọi `_search_records()` trên tập đã lọc. `delete_document()` dùng list comprehension để loại bỏ tất cả record có `metadata["doc_id"] == doc_id`, so sánh độ dài trước và sau để trả về `True/False`.

### KnowledgeBaseAgent

**`answer`** — approach:
> Gọi `self.store.search(question, top_k)` để lấy top-k chunk liên quan. Join nội dung các chunk bằng `\n---\n` làm context. Build prompt theo cấu trúc: `"Context:\n{context}\n\nQuestion: {question}\nAnswer:"` — đặt context trước câu hỏi để LLM có thể grounding câu trả lời vào tài liệu thực. Trả về kết quả của `self.llm_fn(prompt)`.

### Test Results

```
tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | "CMMI giúp cải thiện quy trình phần mềm" | "Mô hình trưởng thành năng lực tích hợp hỗ trợ tổ chức" | high | 0.392 | Không |
| 2 | "Configuration Management kiểm soát phiên bản" | "Quản lý cấu hình đảm bảo tính toàn vẹn sản phẩm" | high | 0.260 | Không |
| 3 | "Trời hôm nay nắng đẹp" | "CMMI V2.0 có 5 mức độ trưởng thành" | low | 0.394 | Không |
| 4 | "Agile và DevOps tương thích với CMMI" | "CMMI V2.0 hỗ trợ phương pháp phát triển linh hoạt" | high | 0.477 | Có |
| 5 | "Maturity Level 3 là Defined" | "Mức độ 1 là Initial chưa có quy trình chuẩn" | low | 0.238 | Có |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
> Pair 3 bất ngờ nhất — câu về thời tiết và câu về CMMI cho score 0.394, cao hơn cả Pair 2 (0.260) dù Pair 2 là hai câu nói về cùng khái niệm (Configuration Management) bằng tiếng Anh và tiếng Việt. Điều này cho thấy model `all-MiniLM-L6-v2` được huấn luyện chủ yếu trên tiếng Anh nên không nắm bắt tốt semantic similarity trong tiếng Việt — cùng một khái niệm diễn đạt bằng tiếng Anh và tiếng Việt có thể cho score thấp hơn dự đoán. Đây là lý do quan trọng khi chọn embedder cho ứng dụng RAG tiếng Việt.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1 | CMMI V2.0 là gì và tại sao nên sử dụng? | CMMI là tập hợp best practices giúp tổ chức cải thiện hiệu suất quy trình; nên dùng vì giúp benchmark năng lực, giảm rủi ro, tăng chất lượng sản phẩm |
| 2 | Practice Area trong CMMI V2.0 gồm những gì? | CMMI V2.0 có 20 Practice Areas gồm CAR, CM, DAR, EST, GOV, II, IRP, MC, MPM, OPD, OPM, OT, PAD, PFM, PI, PLAN, PR, RDM, RSK, SAM |
| 3 | Mức độ trưởng thành (Maturity Level) trong CMMI được phân chia như thế nào? | CMMI có 5 mức: Level 1 (Initial), Level 2 (Managed), Level 3 (Defined), Level 4 (Quantitatively Managed), Level 5 (Optimizing) |
| 4 | Configuration Management (CM) trong CMMI thực hiện những gì? | CM thiết lập và duy trì tính toàn vẹn của sản phẩm công việc thông qua kiểm soát phiên bản, baseline, change control và kiểm toán cấu hình |
| 5 | Lợi ích của việc áp dụng CMMI V2.0 cho tổ chức phát triển phần mềm? | ROI tích cực, giao hàng đúng hạn, kiểm soát chi phí tốt hơn, giảm rework, tăng chất lượng sản phẩm, giảm tỷ lệ nhân viên nghỉ việc |

### Kết Quả Của Tôi

Strategy: `RecursiveChunker(chunk_size=400)` + `LocalEmbedder (all-MiniLM-L6-v2)`
Tổng số chunks: 351 | Avg length: 304 chars

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | CMMI V2.0 là gì và tại sao nên sử dụng? | SAM bao gồm các hoạt động thiết lập thỏa thuận với nhà cung cấp | 0.643 | Một phần | CMMI V2.0 là tập hợp best practices giúp tổ chức cải thiện hiệu suất quy trình, được dùng để benchmark năng lực và lựa chọn nhà cung cấp |
| 2 | Practice Area trong CMMI V2.0 gồm những gì? | Capability Area gồm 2 Practice Areas: Technical Solution (TS) và Product Integration (PI) | 0.704 | Có | CMMI V2.0 gồm các Practice Areas thuộc nhóm Doing như TS, PI, cùng các PA trong Managing và Enabling |
| 3 | Mức độ trưởng thành (Maturity Level) được phân chia như thế nào? | Phân biệt Capability Levels và Maturity Levels trong đánh giá cải tiến quy trình | 0.762 | Có | CMMI có 5 Maturity Levels từ Initial đến Optimizing; Maturity Levels đánh giá mức độ trưởng thành tổng thể khi nhiều PA được triển khai đồng bộ |
| 4 | Configuration Management (CM) trong CMMI thực hiện những gì? | CM đảm bảo tính toàn vẹn của sản phẩm, kiểm soát phiên bản khi nhiều người cùng phát triển | 0.679 | Có | CM thiết lập và duy trì tính toàn vẹn sản phẩm công việc qua kiểm soát phiên bản, baseline, change control và kiểm toán cấu hình |
| 5 | Lợi ích của việc áp dụng CMMI V2.0? | CMMI V2.0 linh hoạt, không bắt buộc áp dụng phương pháp cố định, phù hợp bối cảnh riêng | 0.780 | Có | Áp dụng CMMI V2.0 giúp giao hàng đúng hạn, kiểm soát chi phí, giảm rework, tăng chất lượng và tương thích với Agile/DevOps |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 4 / 5

**Failure case — Query 1:** Retrieval trả về chunk về SAM (Supplier Agreement Management) thay vì định nghĩa tổng quát về CMMI. Lý do: thông tin định nghĩa CMMI V2.0 trải rộng khắp tài liệu, không tập trung trong một đoạn cụ thể nên không có chunk nào có embedding gần với câu hỏi tổng quát. Cải thiện: thêm một chunk tóm tắt riêng ở đầu tài liệu với metadata `section=intro`.

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
> Thành viên dùng SentenceChunker chỉ ra rằng với tài liệu tiếng Việt, ranh giới câu không phải lúc nào cũng là dấu chấm — dấu chấm xuống dòng (`.\n`) và dấu chấm trong số thập phân (`3.0`) có thể gây split nhầm. Điều này khiến tôi hiểu rõ hơn tại sao RecursiveChunker với separator `\n\n` lại ổn định hơn trên tài liệu kỹ thuật có nhiều bullet point và danh sách số thứ tự. Tôi cũng học được cách đo retrieval quality bằng cách so top-1 score thay vì chỉ đếm số chunk.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
> Một nhóm sử dụng metadata `section` để lọc kết quả tìm kiếm theo phần tài liệu trước khi ranking — cách này giảm nhiễu đáng kể khi tài liệu lớn có nhiều chủ đề. Tôi cũng thấy nhóm khác thử nghiệm việc thêm tiêu đề section vào đầu mỗi chunk (chunk enrichment) giúp embedding capture được ngữ cảnh cấp cao hơn, một kỹ thuật tôi chưa áp dụng. Đây là cải tiến tôi sẽ thêm vào nếu tiếp tục dự án này.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
> Trước tiên, tôi sẽ thêm một đoạn tóm tắt giới thiệu (executive summary) vào đầu file `cmmi_nhom2.md` — điều này trực tiếp giải quyết failure case của Query 1 vì thông tin định nghĩa CMMI hiện đang trải rộng khắp tài liệu. Thứ hai, tôi sẽ gán metadata `section` cho từng chunk dựa trên heading Markdown (`##`, `###`) để có thể filter theo Practice Area cụ thể. Thứ ba, tôi sẽ thử embedder đa ngữ như `paraphrase-multilingual-MiniLM-L12-v2` để xử lý tốt hơn nội dung tiếng Việt, đặc biệt cải thiện Pair 2 và Pair 3 trong bài similarity prediction.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 10 / 10 |
| Chunking strategy | Nhóm | 14 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 9 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 5 / 5 |
| **Tổng** | | **88 / 100** |
