# Hệ thống khảo sát & dự báo năng suất dừa — Bản v1.3

Web app khảo sát năng suất dừa qua điện thoại, hoạt động offline, đồng bộ
real-time qua Firebase — theo đúng thiết kế trong "Báo cáo phân tích &
khuyến nghị chuyên gia" (mục 6). Tài liệu này hướng dẫn từng bước triển khai,
viết cho người **chưa biết code**.

## Cấu trúc thư mục

```
webapp/
  index.html                 ← Toàn bộ giao diện + logic (1 file, không cần build)
  firebase-config.sample.js  ← Mẫu cấu hình, đổi tên thành firebase-config.js
  firestore.rules            ← Luật phân quyền dữ liệu (dán vào Firebase Console)
  scripts/
    aggregate_trai_ha_thang.py   ← Tính năng suất dự báo (chạy trên laptop, có Python)
    bulk_create_users.js         ← Tạo hàng loạt 30 tài khoản (chạy 1 lần, có Node.js)
```

## Bước 1 — Tạo dự án Firebase (làm 1 lần)

1. Vào https://console.firebase.google.com, đăng nhập bằng tài khoản Google
   riêng cho dự án (đã thống nhất — không dùng chung Workspace công ty).
2. Bấm **Add project** → đặt tên (ví dụ `khao-sat-dua`) → bỏ chọn Google
   Analytics (không cần) → Create project.
3. Trong dự án, bấm biểu tượng **`</>`** (Web) để đăng ký 1 "web app" →
   đặt tên bất kỳ (ví dụ `khao-sat-web`) → **không** cần tick Firebase Hosting
   ở bước này (mình dùng GitHub Pages) → Register app.
4. Firebase hiện ra khối code `const firebaseConfig = {...}` — copy toàn bộ,
   dán vào file `firebase-config.sample.js`, rồi **đổi tên file** thành
   `firebase-config.js`.
5. Menu trái → **Build → Authentication** → tab Sign-in method → bật
   **Email/Password** → Save.
6. Menu trái → **Build → Firestore Database** → Create database → chọn
   vùng **asia-southeast1 (Singapore)** → bắt đầu ở **Production mode**.
7. Vào tab **Rules** của Firestore → xoá hết nội dung mặc định → dán toàn bộ
   nội dung file `firestore.rules` vào → **Publish**.

## Bước 2 — Tài khoản Admin (đã tạo sẵn)

Claude đã tạo sẵn 1 tài khoản Admin trực tiếp trong Firebase Console:
- Email: `huynhvulinh80@gmail.com`
- Mật khẩu: đã gửi riêng cho anh Linh trong hội thoại — nên đổi lại mật khẩu
  này (Authentication → Users → ⋮ → **Réinitialiser le mot de passe**, hoặc
  thêm chức năng "Đổi mật khẩu" trong app ở bản sau).
- Firestore: đã có document `users/{uid}` với `role: "admin"`,
  `status: "approved"`.

Đăng nhập app bằng tài khoản này sẽ vào thẳng Bảng điều khiển Admin.

## Bước 3 — Tài khoản khảo sát viên: tự đăng ký + Admin duyệt

Bản v1.1 đổi sang cơ chế **tự đăng ký, Admin duyệt** thay vì Admin tạo tay
từng tài khoản:

1. Khảo sát viên mở app → ở màn Đăng nhập bấm **"Đăng ký tại đây"** → nhập
   Họ tên, Email, Mật khẩu tự chọn → Gửi yêu cầu đăng ký.
2. Tài khoản mới tạo ở trạng thái **"chờ duyệt"** — đăng nhập chưa được vào
   app (Firestore Rules chặn tạo phiếu/cây khi chưa duyệt; app tự đăng xuất
   và báo "đang chờ duyệt" nếu khảo sát viên cố đăng nhập trước khi được
   duyệt).
3. Anh Linh đăng nhập Admin → mục **"Tài khoản chờ duyệt"** ngay đầu Bảng
   điều khiển → bấm **Duyệt** hoặc **Từ chối** cho từng người.
4. Sau khi Duyệt, người đó đăng nhập lại là dùng được ngay (không cần Admin
   làm gì thêm).

Ưu điểm: Admin không cần tạo/gửi 29 mật khẩu tạm; mỗi người tự chọn mật khẩu
riêng, và Admin toàn quyền chấp nhận/từ chối trước khi ai đó nhập được dữ
liệu thật.

Lưu ý kỹ thuật: "Từ chối" chỉ chặn ở tầng dữ liệu (Firestore Rules) — tài
khoản đăng nhập (Firebase Auth) vẫn tồn tại vì bản v1.1 chưa có server để
xoá/khoá tài khoản người khác. Nếu cần khoá hẳn, vào Authentication → Users
→ ⋮ → **Désactiver le compte**.

**Cách thay thế (không khuyến nghị, để tham khảo):** script
`scripts/bulk_create_users.js` vẫn dùng được nếu muốn Admin tự tạo tài
khoản hàng loạt thay vì để mọi người tự đăng ký.

## Bản v1.2 — 3 tính năng mới cho Admin & khảo sát viên

1. **Cấu hình trường bắt buộc** (Bảng điều khiển Admin → mục "Cấu hình trường
   bắt buộc"): Admin tick chọn trường nào của phiếu vườn / cây khảo sát là
   bắt buộc nhập. Khảo sát viên sẽ thấy dấu `*` ở trường bắt buộc và không
   lưu được nếu thiếu. Khuyến nghị luôn để "Xã" và "Vị trí GPS" bắt buộc.
2. **Khảo sát viên xem lại phiếu đã thực hiện**: mục "Phiếu của tôi" ở Trang
   chủ giờ hiển thị dạng bảng (ngày, xã, chủ vườn, số cây, trạng thái) — bấm
   "Xem" để vào màn chi tiết phiếu, có đầy đủ thông tin vườn + bảng toàn bộ
   cây đã khảo sát (kèm số trái dự báo theo từng tháng).
3. **Yêu cầu chỉnh sửa phiếu**: phiếu chỉ tự sửa được trong 48 giờ đầu sau khi
   tạo. Sau đó, khảo sát viên vào màn chi tiết phiếu → "Gửi yêu cầu chỉnh
   sửa" (nêu lý do) → Admin vào mục "Yêu cầu chỉnh sửa phiếu" trong Bảng điều
   khiển → Duyệt (mở thêm 48h để sửa) hoặc Từ chối. Nhờ vậy Admin luôn nắm
   được ai sửa gì, sửa khi nào.

*Lưu ý kỹ thuật (đã xử lý, không cần làm gì thêm): mục "Phiếu của tôi" cần 1
chỉ mục kép (composite index) trong Firestore — Claude đã tạo sẵn trong dự án.
Nếu sau này thêm truy vấn tương tự mà bị lỗi "The query requires an index",
Firebase Console sẽ tự đưa link để tạo — bấm vào link đó là xong.*

## Bản v1.3 — Chuẩn hoá dữ liệu Xã, mã cây tự sinh, nâng cấp Bảng điều khiển Admin

Xuất phát từ 1 lỗi dữ liệu thực tế phát hiện khi kiểm thử (2 phiếu ghi "Cẩm
sơn" và "Cẩm Sơn" thành 2 xã khác nhau do gõ tự do), bản này sửa tận gốc và
nâng cấp phần báo cáo:

1. **Xã: dropdown bắt buộc chọn, không cho gõ tự do.** Admin quản lý danh
   sách xã đang khảo sát ở Bảng điều khiển → mục "Cấu hình danh sách Xã khảo
   sát" (thêm/xoá tên xã). Danh sách này tự động đổ vào ô "Xã" của phiếu
   khảo sát dưới dạng dropdown bắt buộc chọn. Khi lưu danh sách, hệ thống tự
   chặn nếu 2 tên chỉ khác nhau hoa/thường (đúng lỗi "Cẩm Sơn"/"Cẩm sơn" đã
   gặp) — buộc Admin gộp lại thành 1 tên trước khi lưu.
2. **Mã cây: tự động gợi ý theo thứ tự, có nút sinh lại, chặn trùng mã.** Khi
   mở màn "Thêm cây", hệ thống tự điền mã kế tiếp (VD: "Cây 01", "Cây 02"…)
   theo đúng thứ tự trong phiếu — khảo sát viên vẫn sửa lại được nếu muốn.
   Nếu lưu trùng mã đã có trong cùng phiếu, hệ thống báo lỗi ngay, không cho
   lưu — tránh nhầm lẫn dữ liệu giữa các cây.
3. **Bảng điều khiển Admin nâng cấp toàn diện:**
   - Sơ đồ trực quan hoá **luồng thông tin theo 6 công đoạn** (thu thập →
     kiểm soát & đồng bộ → Admin kiểm duyệt → phân tích thống kê → kết quả
     dự báo → báo cáo/xuất dữ liệu), mỗi công đoạn hiện trạng thái thực tế
     (số liệu, cảnh báo nếu có việc đang chờ xử lý).
   - Mục báo cáo phân tích & dự báo hiện đầy đủ **phương pháp luận 4 bước**
     (đúng như script `aggregate_trai_ha_thang.py`), **bảng kết quả có đánh
     dấu tháng cao điểm** và mũi tên xu hướng tăng/giảm, cùng **2 biểu đồ**:
     đường dự báo kèm dải khoảng tin cậy 95%, và biểu đồ so sánh theo
     Xã × Nhóm tuổi cây.
   - **3 file xuất riêng biệt**, tạo trực tiếp trong trình duyệt (không cần
     server): (i) dữ liệu thô CSV — đúng bảng cấp cây × tháng dùng làm đầu
     vào phân tích, mở bằng Excel để đối chiếu độc lập; (ii) báo cáo chi
     tiết từng bước (HTML) — đầy đủ phương pháp luận, bảng số liệu theo
     từng tầng, kèm biểu đồ; (iii) tóm tắt cho Ban lãnh đạo (HTML) — 1 trang,
     nêu con số & nhận định chính, kèm 1 biểu đồ, văn phong business.

*Lưu ý: kết quả trong mục "Kết quả dự báo" vẫn do script Python
`aggregate_trai_ha_thang.py` ghi vào Firestore (nguồn dữ liệu chính thức) —
Bảng điều khiển Admin chỉ hiển thị & xuất lại kết quả đó, không tự tính toán
lại bằng JavaScript trong bản chính thức (tránh 2 cách tính khác nhau cùng
tồn tại). Sau khi đổi tên xã cũ, nên chạy lại script Python 1 lần để kết quả
dự báo phản ánh đúng tên xã đã chuẩn hoá.*

## Bước 4 — Đưa web lên GitHub Pages

1. Tạo 1 repository mới trên GitHub của anh (ví dụ `khao-sat-dua-web`),
   để **Public** (GitHub Pages miễn phí yêu cầu Public, trừ khi có GitHub Pro).
2. Upload toàn bộ nội dung thư mục `webapp/` (trừ thư mục `scripts/` — không
   cần đưa lên web) vào repo: `index.html` và `firebase-config.js`.
   *(`firebase-config.js` không phải bí mật — đây là cấu hình công khai của
   ứng dụng web, bảo mật thật sự nằm ở Firestore Rules đã thiết lập ở Bước 1.)*
3. Vào repo → Settings → Pages → chọn nhánh `main`, thư mục `/ (root)` → Save.
4. Sau 1-2 phút, GitHub cho 1 đường link dạng
   `https://<tên-tài-khoản>.github.io/khao-sat-dua-web/` — đây chính là "link
   web" để gửi cho 30 người dùng, lưu vào màn hình chính điện thoại như 1 app.

## Bước 5 — Chạy tính toán năng suất dự báo (định kỳ, trên laptop)

1. Cài Python (nếu laptop chưa có): https://www.python.org/downloads/
2. Mở Command Prompt / Terminal tại thư mục `scripts/`, chạy:
   ```
   pip install firebase-admin pandas numpy
   ```
3. Tải file khoá dịch vụ: Firebase Console → ⚙️ Project settings → Service
   accounts → **Generate new private key** → tải về, đổi tên thành
   `service-account.json`, đặt cùng thư mục `scripts/`.
   *(File này như mật khẩu chủ — không đưa lên GitHub, không chia sẻ.)*
4. (Khuyến nghị) chuẩn bị `dien_tich_theo_tang.csv` (diện tích thật theo
   Xã × Nhóm tuổi cây, lấy từ số liệu đất đai công ty) — xem chú thích đầu
   file `aggregate_trai_ha_thang.py`.
5. Chạy:
   ```
   python aggregate_trai_ha_thang.py
   ```
   Kết quả hiện ngay trên màn hình, lưu vào `ket_qua_trai_ha_thang.csv`, và
   tự động hiện trong mục "Kết quả dự báo mới nhất" ở Bảng điều khiển Admin
   trên web. Chạy lại script này mỗi khi muốn cập nhật số liệu mới (ví dụ
   mỗi tuần/mỗi tháng) — chưa cần tự động hoá ở bản v1.

## Những gì bản v1 CHƯA làm (để biết giới hạn)

- Chưa tự động chạy mô hình GLMM Negative Binomial đầy đủ như đề xuất ở mục
  5.2 báo cáo — script hiện tính trung bình + bootstrap CI (đã đúng tinh
  thần "không giả định phân phối chuẩn", nhưng chưa đưa các biến giống/canh
  tác vào mô hình hồi quy đầy đủ). Sẽ nâng cấp khi có đủ dữ liệu nhiều tháng.
- Cơ chế hậu kiểm bằng dữ liệu thu mua (mục 5.4) là quy trình riêng ngoài
  web app này — không có trong code.
- Admin sửa/xoá phiếu qua giao diện web chưa có nút riêng — có thể sửa/xoá
  trực tiếp trong Firestore Console khi cần (an toàn vì chỉ Admin có quyền).
- Chưa có chức năng chụp ảnh buồng (đề xuất ở mục 7 báo cáo, dùng hậu kiểm
  ngẫu nhiên) — có thể bổ sung sau bằng Firebase Storage.

## Hỏi thêm

Mọi thắc mắc khi làm theo các bước trên, hoặc muốn bổ sung tính năng, cứ
nhắn lại trong cuộc trò chuyện này.
