"""
aggregate_trai_ha_thang.py
==============================================================================
Tính năng suất dừa dự báo theo tháng, đơn vị TRÁI/HA/THÁNG, đúng công thức
4 bước tại mục 5.3 của "Báo cáo phân tích & khuyến nghị chuyên gia":

  ① Cấp cây      : c_i,t  = số trái đếm được ở buồng ứng với tháng dự báo t
  ② Cấp tầng k   : ŷ_i,t  = c_i,t × mật độ trồng của vườn chứa cây i (trái/ha)
                   Ŷ_k,t  = trung bình ŷ_i,t của các cây thuộc tầng k
                   (tầng k = tổ hợp Xã × Nhóm tuổi cây)
  ③ Khoảng tin cậy: bootstrap 2 CẤP (resample theo PHIẾU/VƯỜN trước, rồi theo
                   cây trong vườn) — vì cây lồng trong vườn (dữ liệu cụm),
                   không dùng công thức chuẩn (xem mục 3.2–3.3 báo cáo).
  ④ Gộp vùng     : Ŷ_vùng,t = Σ_k (Diện tích_k / Tổng diện tích) × Ŷ_k,t

Kết quả là "trái/ha/tháng dự kiến (TRẦN)" — CHƯA trừ hao hụt phát sinh sau
khảo sát (sâu bệnh, gãy đổ, thời tiết...). Xem mục 5.4 báo cáo về cơ chế
hậu kiểm (dùng dữ liệu thu mua thực tế) để ước lượng % hao hụt sau này.

------------------------------------------------------------------------------
BẢN v1.6 — TÍNH RIÊNG THEO TỪNG DỰ ÁN

Mỗi cây trong Firestore có sẵn trường "projectId" (ghi ngay lúc khảo sát viên
tạo phiếu). Script này giờ nhóm dữ liệu theo đúng "projectId" của từng cây,
chạy lại đủ 4 bước ở trên RIÊNG cho từng dự án, rồi ghi MỘT document kết quả
riêng cho mỗi dự án vào Firestore (collection "results", có trường "projectId")
— khớp đúng cách các mục khác trên Bảng điều khiển Admin (KPI, tiến độ, thống
kê chuyên sâu, xuất CSV) đã lọc theo dự án từ trước. Cây/phiếu tạo trước khi
có tính năng Dự án (không có "projectId") được gộp vào "legacy-0" ("Dự án 0"),
đúng quy ước đang dùng trong toàn bộ ứng dụng.

Diện tích theo tầng ("dien_tich_theo_tang.csv", nếu có) là dữ liệu đất đai
CÔNG TY — không thay đổi theo dự án — nên vẫn dùng chung 1 bảng cho mọi dự án;
chỉ những tầng THỰC SỰ có trong dữ liệu của từng dự án mới được tính trọng số
(dự án chỉ khảo sát ở 1 vài xã sẽ không bị "loãng" bởi diện tích xã khác).

------------------------------------------------------------------------------
CÁCH DÙNG

1) Cài thư viện (một lần):
     pip install firebase-admin pandas numpy

2) Lấy service account key (một lần):
     Firebase Console → biểu tượng bánh răng → Project settings →
     Service accounts → Generate new private key → tải file .json về,
     đặt cùng thư mục với script này, đặt tên "service-account.json".
     (File này giống mật khẩu — KHÔNG đưa lên GitHub / chia sẻ cho ai.)

3) (Tuỳ chọn nhưng khuyến nghị) Chuẩn bị file diện tích theo tầng:
     "dien_tich_theo_tang.csv" — 3 cột: xa,nhomTuoiCay,dienTich_ha
     Đây là DIỆN TÍCH THỰC TẾ của vùng dự án (không phải diện tích mẫu khảo
     sát) — lấy từ số liệu đất đai/GIS của công ty. Nếu chưa có file này,
     script sẽ tạm dùng tổng diện tích các phiếu ĐÃ khảo sát trong mỗi tầng
     CỦA TỪNG DỰ ÁN (kết quả khi đó chỉ đại diện cho phần diện tích đã khảo
     sát, không phải toàn vùng — sẽ có cảnh báo in ra màn hình).

4) Chạy:
     python aggregate_trai_ha_thang.py

   Script in kết quả ra màn hình theo TỪNG DỰ ÁN, lưu
   "ket_qua_trai_ha_thang.csv" (có cột "projectId"/"projectName"), và ghi
   thẳng vào Firestore (collection "results", 1 document/dự án) để mỗi dự án
   trên Admin dashboard tự hiển thị đúng kết quả của mình. Chạy lại script
   này mỗi khi muốn cập nhật số liệu mới (ví dụ mỗi tuần/mỗi tháng) — chưa
   cần tự động hoá ở bản v1.
==============================================================================
"""

import os
import sys

import numpy as np
import pandas as pd

N_BOOTSTRAP = 1000
CI_LOW, CI_HIGH = 2.5, 97.5
SERVICE_ACCOUNT_FILE = "service-account.json"
AREA_FILE = "dien_tich_theo_tang.csv"
LEGACY_PROJECT_ID = "legacy-0"   # phải khớp đúng hằng số LEGACY_PROJECT_ID trong index.html
LEGACY_PROJECT_NAME = "Dự án 0 (dữ liệu trước khi có tính năng Dự án)"


def load_trees_and_projects_from_firestore():
    import firebase_admin
    from firebase_admin import credentials, firestore

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        sys.exit(
            f"Không tìm thấy {SERVICE_ACCOUNT_FILE}. Xem hướng dẫn ở đầu file "
            "script này (mục 2) để tải service account key từ Firebase Console."
        )

    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    firebase_admin.initialize_app(cred)
    db = firestore.client()

    rows = []
    for doc in db.collection_group("trees").stream():
        d = doc.to_dict()
        survey_id = d.get("surveyId")
        xa = d.get("xa")
        nhom_tuoi = d.get("nhomTuoiCay")
        mat_do = d.get("matDo")
        project_id = d.get("projectId") or LEGACY_PROJECT_ID
        forecast = d.get("forecast", {}) or {}
        for month_tag, count in forecast.items():
            rows.append({
                "projectId": project_id,
                "surveyId": survey_id,
                "xa": xa,
                "nhomTuoiCay": nhom_tuoi,
                "matDo": mat_do,
                "month": month_tag,
                "count": count,
            })

    # Tên dự án để in ra màn hình / ghi vào CSV cho dễ đọc (không bắt buộc phải có).
    project_names = {LEGACY_PROJECT_ID: LEGACY_PROJECT_NAME}
    try:
        for pdoc in db.collection("projects").stream():
            pd_ = pdoc.to_dict() or {}
            project_names[pdoc.id] = pd_.get("name") or pdoc.id
    except Exception:
        pass  # không có quyền/lỗi mạng — vẫn chạy tiếp, chỉ thiếu tên đẹp

    return pd.DataFrame(rows), db, project_names


def load_area_table(df):
    """Diện tích (ha) theo tầng Xã × Nhóm tuổi cây — dùng chung cho mọi dự án
    khi có file thật; nếu không có, trả về None để hàm gọi tự tính trọng số
    tạm thời bằng số vườn đã khảo sát TRONG PHẠM VI df được truyền vào (tức
    riêng theo từng dự án khi gọi trong vòng lặp bên dưới)."""
    if os.path.exists(AREA_FILE):
        area = pd.read_csv(AREA_FILE)
        return area, True

    n_surveys_per_stratum = df.groupby("stratum")["surveyId"].nunique().to_dict()
    return n_surveys_per_stratum, False


def bootstrap_ci(values_by_survey, n_boot=N_BOOTSTRAP):
    """
    values_by_survey: dict {surveyId: [y_i,t của các cây trong vườn đó]}
    Resample 2 cấp: chọn lại danh sách vườn (có lặp), rồi trong mỗi vườn được
    chọn lấy nguyên danh sách cây của vườn đó (giữ cấu trúc cụm).
    """
    survey_ids = list(values_by_survey.keys())
    if len(survey_ids) == 0:
        return np.nan, np.nan, np.nan

    point_estimate = np.mean([v for vs in values_by_survey.values() for v in vs])

    if len(survey_ids) < 2:
        # không đủ cụm để bootstrap có ý nghĩa — trả về điểm ước tính, CI rộng cảnh báo
        return point_estimate, np.nan, np.nan

    boot_means = []
    rng = np.random.default_rng(42)
    for _ in range(n_boot):
        chosen = rng.choice(survey_ids, size=len(survey_ids), replace=True)
        pooled = []
        for sid in chosen:
            pooled.extend(values_by_survey[sid])
        if pooled:
            boot_means.append(np.mean(pooled))
    if not boot_means:
        return point_estimate, np.nan, np.nan
    lo, hi = np.percentile(boot_means, [CI_LOW, CI_HIGH])
    return point_estimate, lo, hi


def compute_forecast_for_project(df_project):
    """Chạy đủ 4 bước phương pháp luận trên dữ liệu ĐÃ LỌC RIÊNG cho 1 dự án.
    Trả về (results_rows, area_is_real) — area_is_real=False nghĩa là đang
    dùng số vườn khảo sát làm trọng số tạm (chưa có file diện tích thật)."""
    area_table_raw, area_is_real = load_area_table(df_project)
    if area_is_real:
        area_table = area_table_raw.set_index(["xa", "nhomTuoiCay"])["dienTich_ha"].to_dict()
    else:
        area_table = area_table_raw  # đã là dict {stratum: n_surveys}

    months = sorted(df_project["month"].unique())
    strata = sorted(df_project["stratum"].unique())
    total_weight = sum(area_table.get(s, 0) for s in strata) or 1

    results_rows = []
    for month in months:
        dmonth = df_project[df_project["month"] == month]
        y_region = 0.0
        stratum_details = []
        for s in strata:
            dstratum = dmonth[dmonth["stratum"] == s]
            if dstratum.empty:
                continue
            values_by_survey = (
                dstratum.groupby("surveyId")["y"].apply(list).to_dict()
            )
            point, lo, hi = bootstrap_ci(values_by_survey)
            weight = area_table.get(s, 0) / total_weight
            y_region += point * weight
            stratum_details.append({
                "xa": s[0], "nhomTuoiCay": s[1],
                "yEstimate": round(point, 1),
                "ciLow": None if np.isnan(lo) else round(lo, 1),
                "ciHigh": None if np.isnan(hi) else round(hi, 1),
                "weight": round(weight, 3),
            })
        results_rows.append({
            "month": month, "value": round(y_region, 1),
            "strata": stratum_details,
        })
    return results_rows, area_is_real


def main():
    df, db, project_names = load_trees_and_projects_from_firestore()
    if df.empty:
        sys.exit("Chưa có dữ liệu cây nào trong Firestore. Chưa thể tính toán.")

    df = df.dropna(subset=["matDo"])
    df["matDo"] = df["matDo"].astype(float)
    df["count"] = df["count"].astype(float)

    # ② y_i,t = c_i,t × mật độ vườn của cây i  (trái/ha, quy đổi mức cây → mức ha)
    df["y"] = df["count"] * df["matDo"]
    df["stratum"] = list(zip(df["xa"], df["nhomTuoiCay"]))

    if not os.path.exists(AREA_FILE):
        print(
            f"[CẢNH BÁO] Không có {AREA_FILE} — tạm dùng tổng diện tích các PHIẾU "
            "ĐÃ khảo sát mỗi tầng CỦA TỪNG DỰ ÁN làm trọng số. Kết quả khi đó chỉ "
            "đại diện cho phần diện tích đã khảo sát, KHÔNG PHẢI toàn vùng dự án. "
            f"Nên bổ sung file {AREA_FILE} (diện tích thật theo Xã × Nhóm tuổi, "
            "lấy từ đất đai/GIS công ty — dùng chung cho mọi dự án) khi có số liệu "
            "để kết quả chính xác hơn.\n"
        )

    from firebase_admin import firestore
    all_csv_rows = []
    project_ids = sorted(df["projectId"].unique())

    for pid in project_ids:
        df_project = df[df["projectId"] == pid]
        pname = project_names.get(pid, pid)
        results_rows, area_is_real = compute_forecast_for_project(df_project)

        print(f"\n=== Dự án: {pname} ({pid}) ===")
        print("Ŷ_vùng,t (trái/ha/tháng, dự kiến TRẦN)"
              + ("" if area_is_real else " — trọng số tạm theo số vườn đã khảo sát"))
        for r in results_rows:
            print(f"  {r['month']}: {r['value']:.0f} trái/ha")

        for r in results_rows:
            for s in r["strata"]:
                all_csv_rows.append({
                    "projectId": pid, "projectName": pname,
                    "month": r["month"], **s,
                })

        forecast_by_month = [
            {"month": r["month"], "value": r["value"],
             "ciLow": min([s["ciLow"] for s in r["strata"] if s["ciLow"] is not None], default=None),
             "ciHigh": max([s["ciHigh"] for s in r["strata"] if s["ciHigh"] is not None], default=None)}
            for r in results_rows
        ]
        db.collection("results").add({
            "projectId": pid,
            "projectName": pname,
            "computedAt": firestore.SERVER_TIMESTAMP,
            "forecastByMonth": forecast_by_month,
            "detail": results_rows,
            "note": "trái/ha/tháng dự kiến (trần) — chưa trừ hao hụt sau khảo sát",
        })

    pd.DataFrame(all_csv_rows).to_csv("ket_qua_trai_ha_thang.csv", index=False, encoding="utf-8-sig")
    print(f"\n[OK] Đã tính xong {len(project_ids)} dự án, lưu chi tiết vào "
          "ket_qua_trai_ha_thang.csv, và ghi kết quả vào Firestore (collection "
          "'results', 1 document/dự án) — mở app, mục Admin → từng dự án để xem.")


if __name__ == "__main__":
    main()
