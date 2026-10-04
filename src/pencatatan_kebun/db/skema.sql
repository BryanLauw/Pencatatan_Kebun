-- Semua id berupa TEXT (UUID) yang dibuat oleh aplikasi.
-- Semua tanggal disimpan sebagai teks format YYYY-MM-DD (urutan teks = urutan waktu).
-- Tampilan DD-MM-YYYY diatur di lapisan ui.

CREATE TABLE IF NOT EXISTS jenis_tanaman (
    id_jenis TEXT NOT NULL PRIMARY KEY,
    nama_jenis VARCHAR(100) NOT NULL COLLATE NOCASE,
    deskripsi TEXT,

    UNIQUE (nama_jenis),
    CHECK (length(trim(nama_jenis)) > 0)
);

CREATE TABLE IF NOT EXISTS varietas (
    id_varietas TEXT NOT NULL PRIMARY KEY,
    id_jenis TEXT NOT NULL,
    nama_varietas VARCHAR(100) NOT NULL COLLATE NOCASE,
    deskripsi TEXT,

    FOREIGN KEY (id_jenis) REFERENCES jenis_tanaman(id_jenis) ON DELETE RESTRICT,
    UNIQUE (id_jenis, nama_varietas),
    CHECK (length(trim(nama_varietas)) > 0)
);

CREATE TABLE IF NOT EXISTS pohon (
    id_pohon TEXT NOT NULL PRIMARY KEY,
    id_jenis TEXT NOT NULL,
    nomor_pohon INTEGER NOT NULL,

    FOREIGN KEY (id_jenis) REFERENCES jenis_tanaman(id_jenis) ON DELETE RESTRICT,
    UNIQUE (id_jenis, nomor_pohon)
);

CREATE TABLE IF NOT EXISTS keterangan_buah (
    id_keterangan TEXT NOT NULL PRIMARY KEY,
    nama_keterangan VARCHAR(100) NOT NULL COLLATE NOCASE,
    deskripsi TEXT,

    UNIQUE (nama_keterangan),
    CHECK (length(trim(nama_keterangan)) > 0)
);

CREATE TABLE IF NOT EXISTS buah (
    id_buah TEXT NOT NULL PRIMARY KEY,
    id_pohon TEXT NOT NULL,
    id_varietas TEXT NOT NULL,
    tanggal_panen DATE NOT NULL,
    id_keterangan TEXT NOT NULL,
    bobot DECIMAL(10, 2) NOT NULL,

    FOREIGN KEY (id_pohon) REFERENCES pohon(id_pohon) ON DELETE RESTRICT,
    FOREIGN KEY (id_varietas) REFERENCES varietas(id_varietas) ON DELETE RESTRICT,
    FOREIGN KEY (id_keterangan) REFERENCES keterangan_buah(id_keterangan) ON DELETE RESTRICT,
    CHECK (bobot > 0),
    CHECK (tanggal_panen IS date(tanggal_panen))
);

-- Varietas buah harus milik jenis yang sama dengan jenis pohonnya (satu pohon
-- bisa berbuah beberapa varietas lewat stek). CHECK tidak bisa melihat tabel
-- lain, jadi dipakai trigger. Jika id tidak ada, foreign key yang menolak.
CREATE TRIGGER IF NOT EXISTS buah_varietas_sesuai_jenis_insert
BEFORE INSERT ON buah
WHEN (SELECT id_jenis FROM pohon WHERE id_pohon = NEW.id_pohon)
     IS NOT (SELECT id_jenis FROM varietas WHERE id_varietas = NEW.id_varietas)
BEGIN
    SELECT RAISE(ABORT, 'Varietas buah tidak sesuai dengan jenis pohon');
END;

CREATE TRIGGER IF NOT EXISTS buah_varietas_sesuai_jenis_update
BEFORE UPDATE OF id_pohon, id_varietas ON buah
WHEN (SELECT id_jenis FROM pohon WHERE id_pohon = NEW.id_pohon)
     IS NOT (SELECT id_jenis FROM varietas WHERE id_varietas = NEW.id_varietas)
BEGIN
    SELECT RAISE(ABORT, 'Varietas buah tidak sesuai dengan jenis pohon');
END;

-- Jenis pohon/varietas tidak boleh dipindah jika sudah ada buah yang memakainya.
CREATE TRIGGER IF NOT EXISTS varietas_jenis_tidak_diubah_jika_dipakai
BEFORE UPDATE OF id_jenis ON varietas
WHEN EXISTS (SELECT 1 FROM buah WHERE id_varietas = OLD.id_varietas)
BEGIN
    SELECT RAISE(ABORT, 'Jenis varietas tidak bisa diubah karena sudah dipakai buah');
END;

CREATE TRIGGER IF NOT EXISTS pohon_jenis_tidak_diubah_jika_dipakai
BEFORE UPDATE OF id_jenis ON pohon
WHEN EXISTS (SELECT 1 FROM buah WHERE id_pohon = OLD.id_pohon)
BEGIN
    SELECT RAISE(ABORT, 'Jenis pohon tidak bisa diubah karena sudah dipakai buah');
END;

CREATE TABLE IF NOT EXISTS periode_panen (
    id_periode TEXT NOT NULL PRIMARY KEY,
    nama_periode VARCHAR(100) NOT NULL,
    tanggal_mulai DATE NOT NULL,
    tanggal_selesai DATE,
    deskripsi TEXT,

    CHECK (length(trim(nama_periode)) > 0),
    CHECK (tanggal_mulai IS date(tanggal_mulai)),
    CHECK (tanggal_selesai IS date(tanggal_selesai)),
    CHECK (tanggal_mulai < tanggal_selesai)
);

-- Periode tidak boleh tumpang tindih (batas sama dihitung tumpang tindih,
-- karena tanggal adalah hari penuh). CHECK tidak bisa melihat baris lain,
-- jadi dipakai trigger.
CREATE TRIGGER IF NOT EXISTS periode_panen_tumpang_tindih_insert
BEFORE INSERT ON periode_panen
WHEN EXISTS (
    SELECT 1 FROM periode_panen
    WHERE NEW.tanggal_mulai <= COALESCE(tanggal_selesai, '9999-12-31')
      AND COALESCE(NEW.tanggal_selesai, '9999-12-31') >= tanggal_mulai
)
BEGIN
    SELECT RAISE(ABORT, 'Periode panen tumpang tindih dengan periode lain');
END;

CREATE TRIGGER IF NOT EXISTS periode_panen_tumpang_tindih_update
BEFORE UPDATE OF tanggal_mulai, tanggal_selesai ON periode_panen
WHEN EXISTS (
    SELECT 1 FROM periode_panen
    WHERE id_periode <> NEW.id_periode
      AND NEW.tanggal_mulai <= COALESCE(tanggal_selesai, '9999-12-31')
      AND COALESCE(NEW.tanggal_selesai, '9999-12-31') >= tanggal_mulai
)
BEGIN
    SELECT RAISE(ABORT, 'Periode panen tumpang tindih dengan periode lain');
END;

CREATE TRIGGER IF NOT EXISTS tutup_periode_panen
BEFORE INSERT ON periode_panen
WHEN EXISTS (
    SELECT 1 FROM periode_panen
    WHERE tanggal_selesai IS NULL AND tanggal_mulai < NEW.tanggal_mulai
)
BEGIN
    UPDATE periode_panen
    SET tanggal_selesai = date(NEW.tanggal_mulai, '-1 day')
    WHERE tanggal_selesai IS NULL AND tanggal_mulai < NEW.tanggal_mulai;
END;
