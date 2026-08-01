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

## sitemap.xml

`scripts/build.py` tự sinh `html/sitemap.xml` (trang chủ + từng trang bài viết, kèm `<lastmod>`
theo `updated_at`) mỗi lần build. URL tuyệt đối lấy từ `site.site_url` (Cấu hình Site trong CMS —
field "URL website"), mặc định `http://giaitri321.com` nếu chưa từng lưu field này (sheet cũ tự
được bổ sung field với giá trị mặc định này ở lần load kế tiếp). Đổi domain thật: sửa field đó
trong CMS rồi lưu lại — không sửa tay `sitemap.xml` hay hardcode domain ở đâu khác.
`html/robots.txt` đã có dòng `Sitemap: ...` trỏ tới file này.

## Schema dữ liệu

- `data/site.json`: `site_name`, `intro_title`, `intro_paragraphs` (mảng string, mỗi phần tử 1
  đoạn `<p>`), `banner: {type: "image"|"video", url, text}`, `menu_games` (mảng string — tên các
  Game hiện ở **menu ngang trên cùng**, xem mục riêng bên dưới), `site_url` (domain thật, dùng
  cho `sitemap.xml`, xem mục riêng bên dưới).
- `data/categories.json`: mảng `{id, slug, name, order}`. `order` = thứ tự hiển thị (kéo-thả
  trong CMS), quyết định thứ tự các section màu xen kẽ trên trang chủ ("DANH SÁCH ..."). **Không
  còn quyết định menu ngang trên cùng** (xem mục Game bên dưới) — chỉ còn dùng để nhóm bài viết
  thành từng khối trên trang chủ. Màu xen kẽ (xanh dương/xanh ngọc cho tiêu đề section, 5 màu xoay
  vòng cho link bài viết) được `build.py` tự tính theo **thứ tự trong mảng**, không lưu màu vào
  data — thêm/bớt/sắp xếp lại category là tự động đổi màu theo, không cần sửa CSS.
- `data/posts.json`: index nhẹ (không có `content`) — title, slug, category_id, game, icon,
  download_type, download_url, download_file_name/_size/_path/_drive_id/_mime, download_storage
  (`"repo"|"release"|"drive"`, xem mục "Giới hạn upload file tải game" bên dưới),
  download_external_url (URL tuyệt đối khi storage là release/drive), download_release_asset_id,
  created_at, updated_at.
- `data/posts/<slug>.json`: như trên + `content` (HTML từ rich-text editor trong CMS).
- Field `game` trên bài viết là **tự do, gõ tay, khác với category** — CMS không ràng buộc nó vào
  danh sách category, chỉ hiển thị làm badge trên trang bài viết (đúng yêu cầu "1 bài viết có thể
  thuộc 1 game nào đó, khác category thường").
- **Menu ngang trên cùng lấy từ Game, không phải Category**: `site.menu_games` là mảng **tên Game
  do admin multi-select** trong CMS (Cấu hình Site) — danh sách để chọn được lấy từ các giá trị
  `game` đã từng gõ ở bài viết (không gõ tay link/tên riêng). Mỗi mục menu bấm vào đều quay về
  trang chủ (`index.html`) — chỉ là danh sách hiển thị/thương hiệu, không lọc/filter gì.
- **Icon đầu tiêu đề** (`post.icon`, tuỳ chọn): `""` (không có) | `hot` | `new` | `game` | `rocket`
  | `fire`, chọn qua nhóm nút trong CMS. `hot`/`new` render badge đỏ; `game`/`rocket`/`fire` render
  emoji 🎮/🚀/🎆. Khi để trống, trang chủ tự cycle qua 1 bộ icon trang trí khác (không có 🎮 trong
  bộ này — 🎮 chỉ hiện khi được chọn chủ động, tránh trùng ý nghĩa với lựa chọn tay).
- **Link tải là tuỳ chọn**: `download_type` có thể là `"none"` (không nhập gì) — bài viết vẫn lưu
  và publish bình thường, chỉ là trang bài viết sẽ không có nút tải (`build.py` tự bỏ qua khi
  thiếu dữ liệu tương ứng với `download_storage`). Khi sửa bài đã upload sẵn file mà không chọn
  file mới, `gas/Code.js` tự giữ nguyên file cũ (không bắt buộc upload lại mỗi lần lưu).

## Setup Google Apps Script

1. Tạo project mới tại [script.google.com](https://script.google.com), xoá `Code.gs` mặc định.
2. Copy nội dung từng file trong `gas/` vào đúng tên file tương ứng trong project
   (`Code.js`, `index.html`, `app.html`, `js.html`, `css.html`) + `appsscript.json`
   (Project Settings → bật "Show appsscript.json").
3. Project Settings → Script Properties, thêm:
   - `GITHUB_TOKEN` — fine-grained PAT, quyền `Contents: Read and write`, giới hạn đúng repo này.
     Quyền này **đã đủ cho cả GitHub Releases** (dùng cho file tải 25MB-2GB) — Releases nằm chung
     nhóm quyền "Contents" của fine-grained PAT, không cần tạo token mới/thêm scope.
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

## Giới hạn upload file tải game (3 tầng lưu trữ theo dung lượng)

File "upload trực tiếp" cho bài viết (khác banner, banner vẫn giữ nguyên 1 tầng, tối đa 100MB,
đẩy thẳng vào repo) giờ tự động chọn nơi lưu cuối cùng theo dung lượng, xem hằng số `DL_TIER_*`
đầu `gas/Code.js`:

| Dung lượng | Nơi lưu | Vì sao |
|---|---|---|
| < 25MB | Repo (Contents API), y hệt cơ chế cũ | Nằm chắc chắn trong trần an toàn của `UrlFetchApp` |
| 25MB – 2GB | 1 asset của **GitHub Release** (tag `game-downloads`, tự tạo) | Endpoint upload riêng (`uploads.github.com`), không qua base64+JSON nên không bị trần ~50MB của Contents API; giới hạn 2GB/asset là do GitHub |
| 2GB – 5GB | **Google Drive**, 1 thư mục riêng tự set "Anyone with link" ngay lần đầu tạo (không cần vào Drive set tay) | Quota Drive không phải giới hạn của code — phụ thuộc dung lượng còn trống của account |
| > 5GB | Từ chối thẳng, báo lỗi rõ ràng | Ngưỡng an toàn tự đặt, dùng "Link tải ngoài" thay vì upload |

Khi sửa bài thay file khác (hoặc bỏ chọn download, hoặc xoá hẳn bài), file CŨ ở đúng nơi nó đang
nằm (repo/Release asset/Drive) sẽ tự được dọn (`cleanupOldDownload_`) — không tích rác quota.

**Nhưng vẫn cần biết trần kỹ thuật thật trước khi hứa "upload tới 5GB" nghe đơn giản:**

3 tầng trên chỉ áp dụng **sau khi bytes đã tới được Apps Script**. Đường đi đưa bytes từ trình
duyệt lên Apps Script (`uploadPostFile`, gọi qua `google.script.run`) vẫn phải mã hoá base64 và
gửi qua tham số của `google.script.run` — bản thân bước này có trần thực tế **thấp hơn nhiều**
so với 2GB/5GB (tương tự trần ~30-40MB đã ghi nhận với `UrlFetchApp` trước đây), vì:

- `FileReader.readAsDataURL()` phải load nguyên file vào RAM trình duyệt trước — file vài trăm MB
  có thể làm tab trình duyệt treo/crash tuỳ máy.
- Payload của `google.script.run` (chuỗi base64, phình to ~33%) cũng có giới hạn thực tế tương tự
  `UrlFetchApp`, không phải do code ở đây tự đặt ra.

**Kết luận thực tế**: logic phân tầng ở trên đúng và sẽ chạy đúng cho **mọi file thực sự upload
lên được**. Nhưng file cỡ vài trăm MB trở lên nhiều khả năng sẽ chậm/thất bại ngay ở bước **chọn
file trong CMS** (trước khi kịp chạm tới logic phân tầng), không phải lỗi của tầng lưu trữ. Muốn
upload tin cậy file thật sự lớn (vài trăm MB – vài GB), hướng đúng là đổi hẳn cơ chế upload: cho
trình duyệt upload thẳng lên Drive bằng Drive resumable upload API, bỏ qua Apps Script ở bước
truyền bytes — đây là thay đổi lớn hơn nhiều, **ngoài phạm vi lần sửa này**.

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
