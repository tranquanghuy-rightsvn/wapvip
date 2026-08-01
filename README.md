# WapVip — CMS + Static Site Pipeline

Kiến trúc theo playbook `free-cms-static-site-pipeline`: Google Apps Script làm CMS (đăng nhập
OTP + Sheets làm DB), mỗi lần Lưu sẽ đẩy dữ liệu lên GitHub qua Contents API, GitHub Actions build
lại `html/` từ `data/` + `templates/`, rồi Vercel/Cloudflare Pages tự deploy.

```
gas/ (CMS)  --commit qua GitHub Contents API-->  data/*.json
                                                     │ (data/posts.json, categories.json, site.json
                                                     │  la file CHOT, trigger CI — xem .github/workflows/build.yml)
                                                     ▼
                                       scripts/build.py + templates/*.html
                                                     │
                                                     ▼
                                              html/ (site tinh) --> hosting
```

## Cấu trúc thư mục

| Thư mục | Ai ghi | Được sửa tay? |
|---|---|---|
| `data/*.json`, `data/posts/<slug>.json` | GAS CMS | **Không** — build lại sẽ mất |
| `html/index.html`, `html/posts/<slug>/index.html` | `scripts/build.py` (CI) | **Không** — bị ghi đè mỗi lần build |
| `html/downloads/<slug>/*`, `html/banner/*` | GAS CMS (ghi thẳng vào site, không qua `data/` để tránh duplicate) | Không cần |
| `templates/index.html`, `templates/post.html` | **Người, tay** | **Có** — đây là chỗ sửa design |
| `html/css/style.css` | Người, tay | Có |
| `scripts/build.py`, `.github/workflows/build.yml` | Người, tay | Có |
| `gas/*` | Người, tay (deploy bằng clasp hoặc copy-paste vào script.google.com) | Có |
| `html/admin/index.html`, `html/robots.txt` | Người, tay | Có (xem mục "Link quản trị") |

Chạy build cục bộ: `python3 scripts/build.py` (chỉ cần Python 3 stdlib, không cần cài gì thêm).
`data/` hiện đang chứa dữ liệu THẬT do CMS ghi vào (không còn data mẫu) — không sửa tay.

## Link quản trị (`/admin/`)

`html/admin/index.html` là 1 trang redirect tĩnh (meta refresh + JS) trỏ sang URL web app GAS
(`/exec`) hiện tại — chỉ để tiện nhớ URL (`domain.com/admin`), không phải trang quản trị thật.
Đổi URL này khi Deploy → New deployment tạo URL `/exec` mới (New version thì URL giữ nguyên,
không cần sửa). Gắn `noindex` 2 lớp để công cụ tìm kiếm không index: meta tag trong chính trang
+ `Disallow: /admin/` trong `html/robots.txt`.

## Schema dữ liệu

- `data/site.json`: `site_name`, `intro_title`, `intro_paragraphs` (mảng string, mỗi phần tử 1
  đoạn `<p>`), `banner: {type: "image"|"video", url, text}`, `menu_games` (mảng string — tên các
  Game hiện ở **menu ngang trên cùng**, xem mục riêng bên dưới).
- `data/categories.json`: mảng `{id, slug, name, order}`. `order` = thứ tự hiển thị (kéo-thả
  trong CMS), quyết định thứ tự các section màu xen kẽ trên trang chủ ("DANH SÁCH ..."). **Không
  còn quyết định menu ngang trên cùng** (xem mục Game bên dưới) — chỉ còn dùng để nhóm bài viết
  thành từng khối trên trang chủ. Màu xen kẽ (xanh dương/xanh ngọc cho tiêu đề section, 5 màu xoay
  vòng cho link bài viết) được `build.py` tự tính theo **thứ tự trong mảng**, không lưu màu vào
  data — thêm/bớt/sắp xếp lại category là tự động đổi màu theo, không cần sửa CSS.
- `data/posts.json`: index nhẹ (không có `content`) — title, slug, category_id, game, icon,
  download_type, download_url, download_file_name/_size/_path/_drive_id/_mime, created_at,
  updated_at.
- `data/posts/<slug>.json`: như trên + `content` (HTML từ rich-text editor trong CMS).
- Field `game` trên bài viết là **tự do, gõ tay, khác với category** — CMS không ràng buộc nó vào
  danh sách category, chỉ hiển thị làm badge trên trang bài viết (đúng yêu cầu "1 bài viết có thể
  thuộc 1 game nào đó, khác category thường").
- **Menu ngang trên cùng lấy từ Game, không phải Category**: `site.menu_games` là mảng **tên Game
  do admin multi-select** trong CMS (Cấu hình Site) — danh sách để chọn được lấy từ các giá trị
  `game` đã từng gõ ở bài viết (không gõ tay link/tên riêng). Mỗi mục menu tự động link về
  `index.html?q=<tên game>`, tái dùng luôn cơ chế search client-side (`data-search`) để lọc đúng
  các bài thuộc game đó — không cần trang danh sách riêng cho từng game.
- **Icon đầu tiêu đề** (`post.icon`, tuỳ chọn): `""` (không có) | `hot` | `new` | `game` | `rocket`
  | `fire`, chọn qua nhóm nút trong CMS. `hot`/`new` render badge đỏ; `game`/`rocket`/`fire` render
  emoji 🎮/🚀/🎆. Khi để trống, trang chủ tự cycle qua 1 bộ icon trang trí khác (không có 🎮 trong
  bộ này — 🎮 chỉ hiện khi được chọn chủ động, tránh trùng ý nghĩa với lựa chọn tay).
- **Link tải là tuỳ chọn**: `download_type` có thể là `"none"` (không nhập gì) — bài viết vẫn lưu
  và publish bình thường, chỉ là trang bài viết sẽ không có nút tải (`build.py` tự bỏ qua khi
  thiếu `download_url`/`download_file_path`). Khi sửa bài đã upload sẵn file mà không chọn file
  mới, `gas/Code.js` tự giữ nguyên file cũ (không bắt buộc upload lại mỗi lần lưu).

## Setup Google Apps Script

1. Tạo project mới tại [script.google.com](https://script.google.com), xoá `Code.gs` mặc định.
2. Copy nội dung từng file trong `gas/` vào đúng tên file tương ứng trong project
   (`Code.js`, `index.html`, `app.html`, `js.html`, `css.html`) + `appsscript.json`
   (Project Settings → bật "Show appsscript.json").
3. Project Settings → Script Properties, thêm:
   - `GITHUB_TOKEN` — fine-grained PAT, quyền `Contents: Read and write`, giới hạn đúng repo này.
   - `GITHUB_REPO` — `<user>/<repo>`.
   - `GITHUB_BRANCH` — tên nhánh chính (bỏ trống = mặc định `master`).
4. Deploy → New deployment → Web app, Execute as **Me**, Who has access **Anyone**.
5. Chạy thử hàm `testGitHubConnection` trong editor 1 lần (Google sẽ hỏi xin quyền truy cập
   Drive/Gmail/External request — bắt buộc phải Allow thì CMS mới chạy được).
6. Mở URL `/exec` vừa deploy, đăng nhập bằng đúng email Google đang sở hữu script (tự động là
   `root`, không cần khai báo gì thêm). Muốn thêm biên tập viên khác: vào tab "Người dùng" trong
   CMS (chỉ root thấy) để thêm email + chọn quyền `editor`/`viewer`.
7. Mỗi khi sửa file trong `gas/*`: phải **Deploy → Manage deployments → Edit → New version**
   (không phải "New deployment") để URL `/exec` cũ nhận code mới — bấm Save trong editor thôi
   là CHƯA đủ.

## Giới hạn upload 100MB (đọc trước khi tin tính năng "upload trực tiếp")

`gas.md` yêu cầu: file tải lên trực tiếp repo bị chặn nếu vượt 100MB. Điều này đã được implement
đúng ở cả client (`onPostFileChosen`/`onBannerFileChosen`) lẫn server (`uploadPostFile`,
`uploadBannerFile`, `savePost`, `saveSiteSettings` đều re-check).

**Nhưng cần biết rõ trần kỹ thuật thật của Apps Script trước khi hứa với khách/người dùng:**

- `UrlFetchApp` (dùng để gọi GitHub Contents API) có giới hạn thực tế **~50MB/request** (cả
  chiều gửi lẫn nhận), không phải do code ở đây tự đặt ra.
- File phải mã hoá base64 trước khi nhét vào JSON gửi GitHub — base64 làm payload phình to
  thêm **~33%**. Một file 100MB sẽ thành ~133MB base64 → chắc chắn vượt trần 50MB của
  `UrlFetchApp`, request sẽ lỗi (hoặc timeout) chứ không chạy được như mô tả "cho phép tới
  100MB" nghe có vẻ đơn giản.
- Việc đọc file thành base64 ngay trên trình duyệt (`FileReader.readAsDataURL`) với file gần
  100MB cũng có thể chậm/tốn RAM tuỳ máy người dùng.

**Kết luận thực tế**: cơ chế "upload trực tiếp" trong CMS này chạy tốt và đáng tin cậy với file
**dưới ~30-40MB**. Trên ngưỡng đó, khả năng cao sẽ lỗi ở bước đẩy GitHub dù UI báo "upload xong"
(vì bước đó chỉ mới lưu tạm vào Drive — lỗi thật sự xảy ra ở lúc bấm Lưu bài, khi GAS đọc bytes
từ Drive rồi gọi GitHub). Đây là lý do UI đã có dòng khuyến nghị dùng "Link tải ngoài" cho file
lớn — **không lặng lẽ để tính năng trông như hoạt động rồi âm thầm fail ở file to**. Nếu thực tế
cần hỗ trợ file sát ngưỡng 100MB thật, hướng đúng là nâng cấp sang Git Data API (trees, atomic hơn
nhưng vẫn cùng trần `UrlFetchApp`) hoặc — thực tế hơn — chuyển hẳn file lớn sang 1 dịch vụ lưu trữ
ngoài (Drive share link, hoặc CDN riêng) và chỉ lưu link, tức là dùng option 1 (link tải ngoài)
thay vì option 2.

## Trạng thái hiện tại

- `data/`, `templates/`, `scripts/build.py`, `.github/workflows/build.yml` đã viết xong và
  **test bằng dữ liệu mẫu** (4 category, 4 bài viết) — `python3 scripts/build.py` chạy được,
  idempotent (chạy 2 lần liên tiếp không sinh diff thừa), đã xem output trong trình duyệt
  (trang chủ + trang bài viết render đúng, nút tải nổi không đè content).
- `gas/*` đã viết xong nhưng **chưa từng deploy/test thật với 1 Apps Script project + repo GitHub
  thật** (môi trường này không có Google account/GitHub repo để deploy) — làm theo mục "Setup
  Google Apps Script" ở trên, rồi test kỹ luồng Lưu bài/category/banner với dữ liệu thật trước
  khi giao cho người không rành kỹ thuật dùng.
- Dữ liệu mẫu trong `data/` chỉ để demo/test build — xoá hết (giữ file rỗng `[]`/`{}` đúng
  schema) trước khi CMS thật bắt đầu ghi dữ liệu.
