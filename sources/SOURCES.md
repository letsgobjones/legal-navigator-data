# Sources

The official documents every JSON in this repo is built from. The PDFs themselves are not committed (see `.gitignore`); download them to the paths below. The SHA-256 checksum confirms you have the exact file the current JSON was built from.

```bash
shasum -a 256 sources/*/*.pdf
```

## KBLI 2025: `sources/kbli_2025/`

Klasifikasi Baku Lapangan Usaha Indonesia 2025, Badan Pusat Statistik (established by Peraturan BPS No. 7 Tahun 2025).

| File | Source | Downloaded | SHA-256 |
|---|---|---|---|
| `klasifikasi-baku-lapangan-usaha-indonesia--kbli--2025--2.pdf` | BPS, [bps.go.id](https://www.bps.go.id) (exact URL not recorded) | 2026-09-29 | `169ec324af12c3e535d081dbe3789e019f9131ab81460357c2453fd0651a56b3` |

Used by: `kbli/parse_kbli.py`. The same PDF also contains BPS's KBLI 2020 → 2025 change tables (Tabel 5.2.1–5.2.22), which could be parsed later as an independent check on OSS's conversions.

## PP 28 Tahun 2025: `sources/pp28_2025/`

Peraturan Pemerintah No. 28 Tahun 2025 tentang Penyelenggaraan Perizinan Berusaha Berbasis Risiko. In force since 2025-06-05; revokes PP 5 Tahun 2021. Status checked on 2026-09-30: *Berlaku*, no amendments listed.

Details page: <https://peraturan.bpk.go.id/Details/319773/pp-no-28-tahun-2025>

Download URL pattern: `https://peraturan.bpk.go.id/Download/<id>/<file name>`.

| File (saved as) | BPK id | Contents | Downloaded | SHA-256 |
|---|---|---|---|---|
| `PP Nomor 28 Tahun 2025.pdf` | 381375 | Main regulation (383 pp.) | 2026-09-30 | `8808de485eab2499cf3d8369921c097beaea68ae55aa767c61095d47a5a118fb` |
| `Lampiran I.C (I.C.1-182).pdf` | 394932 | Sektor Kehutanan | 2026-09-30 | `23a5d78db191504c04a06db4f4569299a823c283b30f35faeda7fce8aeff910a` |
| `Lampiran I.F (I.F.1-700).pdf` | 394935 | Sektor Perindustrian, part a (KBLI 10130–11010) | 2026-09-30 | `fcdadc0ec9d831e0e4e8ddad18178ad972cee2c1a7aa79eff42a8ee6c7438ed3` |
| `Lampiran III.pdf` | 394949 | Metode analisis risiko | 2026-09-30 | `55b71be9e4dcff28cdec24b7242663358b42e3ce41edb45ae7da07bc41e2921e` |
| `Lampiran IV.pdf` | 394950 | Pedoman standar kegiatan usaha / produk | 2026-09-30 | `63bd92a6a0dd94d73746b81cc3bf8eed6aefc16ff2f7b13e06b3fc232da2a8aa` |

Not downloaded yet:

| BPK id | Published file name |
|---|---|
| 394930 | 2.1 Lampiran I.A PP Nomor 28 Tahun 2025 (I.A.1-364).pdf |
| 394931 | 2.2 Lampiran I.B PP Nomor 28 Tahun 2025 (I.B.1-810).pdf |
| 394933 | 2.4 Lampiran I.D PP Nomor 28 Tahun 2025 (I.D.1-1056).pdf |
| 394934 | 2.5 Lampiran I.E PP Nomor 28 Tahun 2025 (I.E.1-189).pdf |
| 394936 | 2.6b Lampiran I.F PP Nomor 28 Tahun 2025 (I.F.701-1400).pdf |
| 394937 | 2.6c Lampiran I.F PP Nomor 28 Tahun 2025 (I.F.1401-2125).pdf |
| 394938 | 2.6d Lampiran I.F PP Nomor 28 Tahun 2025 (I.F.2126-2922).pdf |
| 394939 | 2.6e. Lampiran I.F PP Nomor 28 Tahun 2025 (I.F.2923-3680).pdf |
| 394940 | 2.6f Lampiran I.F PP Nomor 28 Tahun 2025 (I.F.3681-4500).pdf |
| 394941 | 2.6g Lampiran I.F PP Nomor 28 Tahun 2025 (I.F.4501-5248).pdf |
| 394942 | 2.6h Lampiran I.F PP Nomor 28 Tahun 2025 (I.F.5249-11000).pdf |
| 394943 | 2.7 Lampiran I.G PP Nomor 28 Tahun 2025 (I.G.1-341).pdf |
| 394944 | 2.8 Lampiran I.H PP Nomor 28 Tahun 2025 (I.H.1-515).pdf |
| 394945 | 2.9 Lampiran I.I PP Nomor 28 Tahun 2025 (I.I.1-411).pdf |
| 394946 | 2.10 Lampiran I.J sd. I.P PP Nomor 28 Tahun 2025.pdf |
| 394947 | 2.11 Lampiran I.Q sd. I.V PP Nomor 28 Tahun 2025.pdf |
| 394948 | PP Nomor 28 Tahun 2025 - Lampiran II.pdf |

## Related, not yet used

- **SEB on implementing KBLI 2025 in OSS** (2026-03-27). OSS switched to KBLI 2025 on 2026-06-15; licenses issued before then remain valid. Announcement: <https://www.bkpm.go.id/id/info/pengumuman/seb-kementerian-investasi-dan-hilirisasi-kepala-bkpm-tentang-implementasi-penyesuaian-kbli>
- **Permen Investasi/BKPM No. 5 Tahun 2025**, the implementing regulation for PP 28/2025.
