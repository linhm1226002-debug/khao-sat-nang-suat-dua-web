# Hệ thống khảo sát & dự báo năng suất dừa — Bản v1.5

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

## Bản v1.4 — Quản lý theo Dự án, KPI từng khảo sát viên, tuỳ chỉnh biểu đồ, thống kê chuyên sâu

Bản này chuyển toàn bộ cách vận hành sang **quản lý theo dự án khảo sát**
(thay vì 1 luồng dữ liệu chung duy nhất), đồng thời nâng chiều sâu phân tích
và cá nhân hoá biểu đồ theo yêu cầu thực tế:

1. **Dự án khảo sát (mở/đóng theo đợt, theo phạm vi xã, theo mốc thời gian).**
   Admin tạo dự án mới ở mục "🗂 Quản lý dự án" (Bảng điều khiển): đặt tên,
   mô tả, ngày bắt đầu/kết thúc, số tháng dự báo mỗi cây (có thể khác nhau
   giữa các dự án, VD dự án 3 tháng vs. 7 tháng), và phạm vi xã áp dụng (toàn
   bộ xã, hoặc chỉ một số xã cụ thể). Có thể **mở nhiều dự án song song** —
   mỗi khảo sát viên chọn đúng dự án đang nhập liệu ở Trang chủ, dropdown "Xã"
   tự lọc theo đúng phạm vi của dự án đó. "Lưu trữ" dự án chỉ ẩn khỏi danh
   sách đang mở (theo đúng yêu cầu — **không xoá dữ liệu**), Admin vẫn xem/
   xuất báo cáo lại bất cứ lúc nào qua mục "Dự án đang xem", và có thể khôi
   phục lại thành đang mở. Toàn bộ phiếu/cây dữ liệu trước khi có tính năng
   này đã được gộp vào "Dự án 0 (dữ liệu trước khi có tính năng Dự án)" ở
   trạng thái lưu trữ, không mất dữ liệu cũ.
2. **KPI theo từng khảo sát viên, riêng theo từng dự án.** Ở mỗi dự án, Admin
   đặt chỉ tiêu số phiếu / số cây cho từng khảo sát viên (mục "🎯 Chỉ tiêu
   KPI" trong khung quản lý dự án). Mục "Hiệu suất từng khảo sát viên" so
   sánh trực tiếp số thực hiện so với chỉ tiêu (thanh tiến độ %), và callout
   "Tiến độ dự án" so sánh **% thời gian dự án đã qua** với **% khối lượng
   công việc đã hoàn thành so với chỉ tiêu**, tự cảnh báo màu (bình thường /
   chậm nhẹ / chậm đáng kể) để phân bổ lại công việc kịp thời.
3. **Tuỳ chỉnh biểu đồ trực tiếp trên Bảng điều khiển.** Biểu đồ đường (dự
   báo) và biểu đồ cột (theo tầng) đều có thanh tuỳ chọn: bật/tắt nhãn số
   liệu (data labels), vị trí nhãn (trên/dưới điểm), làm mượt đường (smoothed
   line), đổi màu. Tuỳ chỉnh áp dụng nhất quán cho cả biểu đồ xem trực tiếp
   và biểu đồ trong các file báo cáo xuất ra (HTML).
4. **Báo cáo phân tích chuyên sâu theo thống kê (mục "Phân tích thống kê
   chuyên sâu theo tháng" trong báo cáo chi tiết).** Bổ sung: bảng mô tả
   thống kê chuẩn kiểu SPSS (trung bình, độ lệch chuẩn, trung vị, tứ phân vị,
   skewness/kurtosis có hiệu chỉnh sai số chuẩn) và biểu đồ histogram cho
   từng tháng dự báo; kiểm định Jarque-Bera đánh giá phân phối chuẩn; phân
   tích phương sai đo lặp một yếu tố (repeated-measures ANOVA) so sánh khác
   biệt năng suất **giữa các tháng trên cùng một cây** kèm hệ số ảnh hưởng
   (partial eta²); so sánh cặp tháng có hiệu chỉnh Bonferroni để xác định cụ
   thể cặp tháng nào khác biệt có ý nghĩa thống kê. Toàn bộ tính theo **vị trí
   tháng tương đối** (tháng thứ 1, 2, 3... kể từ lúc khảo sát) thay vì tháng
   lịch tuyệt đối, để tránh gộp nhầm dữ liệu từ các phiếu tạo ở thời điểm
   khác nhau.

*Giới hạn đã biết: script Python `aggregate_trai_ha_thang.py` (mục "Kết quả
dự báo") và các báo cáo do script này tạo (biểu đồ đường/cột chính, bảng dự
báo, tóm tắt Ban lãnh đạo) **chưa lọc theo từng dự án** — vẫn tính trên toàn
bộ dữ liệu như trước. Phần lọc theo dự án trong bản v1.4 áp dụng cho: luồng
thông tin 6 công đoạn, KPI theo xã/theo khảo sát viên, tiến độ dự án, phân
tích thống kê chuyên sâu, và xuất dữ liệu thô CSV. Sẽ nâng cấp script Python
để nhận biết dự án khi có nhu cầu tách báo cáo dự báo riêng theo từng dự án.*

## Bản v1.5 — Tách Admin Hub/Chi tiết dự án/Cài đặt, wizard tạo dự án, thùng rác, bảng dữ liệu cây + loại trừ, bản đồ, histogram có đường mật độ, chạy phân tích thủ công, rà soát bảo mật

Bản này thiết kế lại toàn bộ khu vực Admin theo hướng chuyên nghiệp hơn, tách
bạch rõ 3 việc trước đây gộp chung 1 trang dài:

1. **Admin Hub (danh mục dự án + tổng quan).** Đăng nhập Admin giờ vào thẳng
   trang "📁 Danh mục dự án" — chỉ hiện: 4 số tổng quan toàn hệ thống (số dự
   án đang mở, tổng phiếu, tổng cây, số xã có dữ liệu), thẻ từng dự án (bấm
   "Xem chi tiết →" để vào báo cáo), và mục "⚙️ Cài đặt hệ thống" riêng. Bảng
   điều khiển 1 trang dài trước đây được tách thành 3 màn hình logic:
   - **Hub** — danh mục & tổng quan (trang này).
   - **Chi tiết 1 dự án** — luồng thông tin, KPI, tiến độ, hiệu suất khảo sát
     viên, dữ liệu đầu vào, phân tích thống kê, báo cáo & xuất dữ liệu.
   - **Cài đặt hệ thống** — tài khoản chờ duyệt, yêu cầu chỉnh sửa phiếu,
     danh sách xã, trường bắt buộc, mục tiêu KPI theo xã, phenology.
2. **Wizard tạo dự án mới (4 bước).** Bấm "+ Tạo dự án mới" ở Hub mở hộp
   thoại theo từng bước: Thông tin cơ bản → Thời gian & số tháng dự báo →
   Phạm vi xã → Xác nhận (xem lại toàn bộ trước khi tạo) — tránh tạo nhầm dự
   án do điền thiếu/sai giữa các trường liên quan.
3. **Xoá dự án có thùng rác, tự xoá vĩnh viễn sau 90 ngày.** Mỗi thẻ dự án ở
   Hub có nút "🗑 Xoá" — chuyển dự án vào Thùng rác (vẫn hiện ở cuối trang
   Hub, đếm ngược số ngày còn lại), có thể "↩ Khôi phục" hoặc "❌ Xoá vĩnh
   viễn ngay" bất cứ lúc nào trong 90 ngày; sau 90 ngày hệ thống tự xoá vĩnh
   viễn khi Admin mở lại trang Hub. **Xoá dự án KHÔNG xoá phiếu/cây đã ghi
   nhận** — chỉ xoá thông tin dự án, dữ liệu khảo sát luôn được giữ an toàn
   (giống cách "Dự án 0" lưu trữ dữ liệu trước v1.4).
4. **Bảng dữ liệu từng cây + loại trừ khỏi phân tích (có thể khôi phục).**
   Trong Chi tiết dự án, mục "🔎 Dữ liệu đầu vào" có bảng chi tiết đến từng
   cây (mã cây, xã, nhóm tuổi, mật độ, tổng dự kiến), tìm kiếm theo mã cây,
   lọc theo xã/trạng thái. Mỗi dòng có nút "🚫 Loại trừ" / "↩ Khôi phục" —
   cây bị loại trừ vẫn còn nguyên trong Firestore (KHÔNG xoá), chỉ tạm ẩn
   khỏi bước tính thống kê chuyên sâu — dùng khi phát hiện cây ghi số liệu
   rõ ràng sai (VD: gõ nhầm số trái) mà chưa kịp sửa tận gốc.
5. **Bản đồ vị trí khảo sát (Leaflet + OpenStreetMap, miễn phí) + timeline.**
   Tab "🗺️ Bản đồ vị trí" hiện từng điểm GPS đã ghi nhận (theo phiếu/vườn —
   GPS hiện lấy 1 lần/vườn, chưa lấy riêng từng cây), bấm vào điểm xem chủ
   vườn/ngày khảo sát/số cây/tổng dự kiến. Thanh trượt + nút "▶ Phát" cho
   xem lại các vườn xuất hiện dần theo đúng thứ tự ngày khảo sát thực tế.
6. **Histogram có đường cong mật độ chuẩn (giống hình SPSS tham khảo) +
   tương tác click lọc bảng.** Mỗi histogram trong mục phân tích chuyên sâu
   giờ có thêm đường cong chuẩn (Normal fit theo Mean/SD mẫu) vẽ chồng lên,
   đúng kiểu trình bày SPSS "Explore". Bấm vào 1 cột sẽ tự lọc "Bảng dữ liệu
   cây" theo đúng khoảng giá trị + đúng "tháng thứ N" của cột đó, giúp xem
   ngay những cây nào đang rơi vào khoảng bất thường.
7. **Chạy phân tích thống kê thủ công (2 bước tách biệt).** Trước đây thống
   kê chuyên sâu tự tính ngay khi mở trang. Từ bản này, Admin cần: (1) rà
   soát dữ liệu đầu vào (bảng cây, bản đồ, loại trừ cây sai sót nếu có) →
   (2) chủ động bấm "▶ Chạy phân tích thống kê" mới ra kết quả — tránh đọc
   nhầm kết quả tính trên dữ liệu chưa được rà soát. Mỗi khi loại trừ/khôi
   phục 1 cây, hệ thống tự yêu cầu chạy lại phân tích.
8. **Rà soát bảo mật.**
   - **Chống XSS lưu trữ:** toàn bộ dữ liệu tự do người dùng nhập (tên, ghi
     chú yêu cầu sửa phiếu, mã cây, tên xã, mô tả dự án…) nay được `escapeHtml()`
     trước khi hiển thị lại — chặn khả năng 1 tài khoản khảo sát viên chèn mã
     độc vào ô nhập liệu để chạy trong phiên trình duyệt của Admin.
   - **Firestore Rules:** đã rà soát lại — trạng thái "trashed" (thùng rác) và
     trường `excludedFromAnalysis` (loại trừ cây) đều nằm trong phạm vi
     `allow write: if isAdmin()` đã có sẵn từ trước, không cần rule mới; xem
     ghi chú chi tiết ngay trong file `firestore.rules`.
   - **Giới hạn cần biết:** Rules chỉ bảo vệ được **dữ liệu** (ai đọc/ghi được
     gì) — KHÔNG thể "giấu" mã nguồn HTML/CSS/JS phía trình duyệt (đây là giới
     hạn chung của mọi trang web tĩnh, không phải lỗ hổng riêng của app này).
     Nếu lo ngại đối thủ copy giao diện, cách xử lý thực tế là thương hiệu/
     bản quyền, không phải kỹ thuật che mã nguồn. Khuyến nghị bổ sung (làm
     trên Firebase/Google Cloud Console, xem chi tiết trong `firestore.rules`):
     giới hạn API key theo domain (HTTP referrers), cân nhắc bật Firebase App
     Check, và định kỳ rà soát danh sách tài khoản chờ duyệt/đã duyệt.

*Giới hạn đã biết của bản v1.5: việc tự xoá thùng rác sau 90 ngày chỉ chạy
khi Admin MỞ trang Hub (app không có server/cron riêng để tự chạy lúc không
ai mở app) — nếu 90 ngày trôi qua mà không ai đăng nhập Admin, dự án vẫn nằm
im trong thùng rác đến lần đăng nhập kế tiếp, không tự "biến mất" đúng giờ.
Bản đồ hiện đại diện theo VƯỜN (phiếu khảo sát), chưa có GPS riêng từng cây —
nếu cần độ chính xác đến từng cây, cần bổ sung bước lấy GPS ở màn "Thêm cây"
(hiện chưa có, vì tăng thời gian nhập liệu ngoài đồng).*

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
