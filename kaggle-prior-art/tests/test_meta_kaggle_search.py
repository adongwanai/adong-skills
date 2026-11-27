import csv
import json
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import meta_kaggle_search as mk

COMPS = [
    ["1", "asap-aes", "Automated Essay Scoring", "Score student essays", "Featured", "10",
     "Quadratic Weighted Kappa", "QWK", "04/30/2012 23:59:00", "150"],
    ["2", "learning-agency-lab-automated-essay-scoring-2", "Learning Agency Lab - Automated Essay Scoring 2.0",
     "Improve essay scoring", "Featured", "20", "Quadratic Weighted Kappa", "QWK", "07/02/2024 23:59:00", "2700"],
    ["3", "titanic-class", "Essay homework", "class exercise", "InClass", "30",
     "Quadratic Weighted Kappa", "QWK", "05/01/2024 00:00:00", "12"],
    ["4", "cs229-essay-community", "Essay Scoring Bootcamp", "student homework", "Community", "35",
     "Quadratic Weighted Kappa", "QWK", "08/01/2025 00:00:00", "8"],
    ["5", "house-prices", "House Prices", "regression", "Getting Started", "40",
     "Root Mean Squared Error", "RMSE", "01/01/2030 00:00:00", "5000"],
]
HEADER = ["Id", "Slug", "Title", "Subtitle", "HostSegmentTitle", "ForumId",
          "EvaluationAlgorithmName", "EvaluationAlgorithmAbbreviation", "DeadlineDate", "TotalTeams"]

TOPICS = [
    ["101", "20", "1st Place Solution", "300", "07/05/2024"],
    ["102", "20", "Thanks to the hosts", "50", "07/05/2024"],
    ["103", "20", "Public 2nd (Private 30th) Place Solution", "40", "07/05/2024"],
    ["104", "20", "3rd place solution & code", "120", "07/05/2024"],
    ["105", "20", "Top 5% solution notes", "5", "07/06/2024"],
    ["106", "20", "Question about place in the LB", "3", "06/01/2024"],
    ["107", "20", "2nd Public / 5th Private Solution", "95", "07/05/2024"],
    ["108", "20", "#2 Solution & Code", "210", "07/05/2024"],
    ["109", "20", "When will 1st place solution be posted?", "15", "07/03/2024"],
    ["110", "20", "Submission scoring error - any solution?", "8", "06/10/2024"],
    ["111", "20", "First time here, how to place on LB?", "4", "06/12/2024"],
    ["112", "20", "May 1st update: our approach to CV", "12", "05/01/2024"],
    ["113", "10", "Winning approach: 1st place", "80", "05/01/2012"],
]
TOPIC_HEADER = ["Id", "ForumId", "Title", "Score", "CreationDate"]

SAMPLE_FARID_YAML = """competitions:
  - number: "700"
    title: "Learning Agency Lab - Automated Essay Scoring 2.0"
    desc: "Improve upon essay scoring algorithms"
    kind: "Featured"
    prize: "$50,000"
    team: "2,706"
    metric: "Cohen Kappa Score"
    link: "https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2"
    year: "2024"
    done: "true"
    solutions:
      - rank: "1"
        link: "https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/516791"
        kind: "description"
      - rank: "3"
        link: "https://github.com/example/aes2-3rd-place"
        kind: "code"
      - rank: "12"
        link: "https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/writeups/12th-place-up-350-places"
        kind: "description"
      - rank: ""
        link: "https://www.kaggle.com/c/learning-agency-lab-automated-essay-scoring-2/discussion/999999"
        kind: "description"
  - number: "699"
    title: "Child Mind Institute"
    desc: "Problematic Internet Use"
    kind: "Featured"
    prize: "$60,000"
    team: "3,559"
    metric: "Cohen Kappa Score"
    link: "https://www.kaggle.com/c/child-mind-institute-problematic-internet-use"
    year: "2024"
    done: "true"
    solutions:
      - rank: "1"
        link: "https://www.kaggle.com/c/child-mind-institute-problematic-internet-use/discussion/552638"
        kind: "description"
"""


def write_csv(path, header, rows, encoding="utf-8"):
    with open(path, "w", newline="", encoding=encoding) as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def run(capsys, *args):
    mk.main(list(args))
    return json.loads(capsys.readouterr().out)


def test_keyword_metric_year_inclass_and_community(tmp_path, capsys):
    write_csv(tmp_path / "Competitions.csv", HEADER, COMPS)
    out = run(capsys, "--data-dir", str(tmp_path), "--keywords", "essay", "--metric", "qwk")
    slugs = [c["slug"] for c in out["competitions"]]
    # Both InClass and Community noise competitions are filtered out; metric alias 'qwk' matches QWK
    assert slugs == ["learning-agency-lab-automated-essay-scoring-2", "asap-aes"]
    assert out["search_strategy"] == "direct"

    out = run(capsys, "--data-dir", str(tmp_path), "--keywords", "essay", "--since-year", "2020")
    assert [c["slug"] for c in out["competitions"]] == ["learning-agency-lab-automated-essay-scoring-2"]

    out = run(capsys, "--data-dir", str(tmp_path), "--keywords", "essay", "--include-inclass")
    included = [c["slug"] for c in out["competitions"]]
    assert "titanic-class" in included and "cs229-essay-community" in included

    out = run(capsys, "--data-dir", str(tmp_path), "--keywords", "essay", "--min-teams", "500")
    assert [c["slug"] for c in out["competitions"]] == ["learning-agency-lab-automated-essay-scoring-2"]

    out = run(capsys, "--data-dir", str(tmp_path), "--metric", "rmse")
    assert [c["slug"] for c in out["competitions"]] == ["house-prices"]


def test_short_keyword_word_boundary(tmp_path, capsys):
    rows = [
        ["1", "general-energy", "General Energy Partner", "Winner owner", "Featured", "1", "RMSE", "RMSE", "2024", "500"],
        ["2", "clinical-ner", "Medical NER Challenge", "Named entity", "Featured", "2", "F1", "F1", "2024", "500"],
    ]
    write_csv(tmp_path / "Competitions.csv", HEADER, rows)
    out = run(capsys, "--data-dir", str(tmp_path), "--keywords", "ner")
    assert [c["slug"] for c in out["competitions"]] == ["clinical-ner"]


def test_solution_threads_zip_bom_and_noise_filtering(tmp_path, capsys):
    write_csv(tmp_path / "Competitions.csv", HEADER, COMPS)
    # Write ForumTopics with UTF-8 BOM (\ufeffId) inside a .zip archive
    write_csv(tmp_path / "ForumTopics.csv", TOPIC_HEADER, TOPICS, encoding="utf-8-sig")
    with zipfile.ZipFile(tmp_path / "ForumTopics.csv.zip", "w") as z:
        z.write(tmp_path / "ForumTopics.csv", "ForumTopics.csv")
    os.remove(tmp_path / "ForumTopics.csv")

    out = run(capsys, "--data-dir", str(tmp_path), "--keywords", "essay", "--metric", "kappa", "--solutions")
    aes2 = out["competitions"][0]
    threads = [(t["place"], t["title"]) for t in aes2["solution_threads"]]

    assert threads[0] == (1, "1st Place Solution")
    assert (2, "#2 Solution & Code") in threads
    assert (3, "3rd place solution & code") in threads
    assert (5, "2nd Public / 5th Private Solution") in threads          # private rank before word 'Private'
    assert (30, "Public 2nd (Private 30th) Place Solution") in threads  # private rank after word 'Private'
    assert (None, "Top 5% solution notes") in threads                   # percentage is not an ordinal rank

    titles = [t for _, t in threads]
    for bad in ("Thanks", "Question", "When will", "scoring error", "First time", "May 1st"):
        assert all(bad not in t for t in titles), f"Noise thread leaked: {bad}"

    assert out["competitions"][1]["solution_threads"][0]["place"] == 1


def test_tags_and_shakeup_radar(tmp_path, capsys):
    rows = [
        ["99", "hms-brain", "HMS Harmful Brain Activity", "Classify signals", "Featured", "90",
         "Kullback-Leibler", "KL", "04/01/2024", "1000"],
    ]
    write_csv(tmp_path / "Competitions.csv", HEADER, rows)
    write_csv(tmp_path / "Tags.csv", ["Id", "Name", "Slug"], [["7", "eeg time-series", "eeg"]])
    write_csv(tmp_path / "CompetitionTags.csv", ["CompetitionId", "TagId"], [["99", "7"]])
    # Simulate big shake-up among top 10 private finishers
    team_rows = [["99", str(200 + i * 20), str(i)] for i in range(1, 12)]
    write_csv(tmp_path / "Teams.csv", ["CompetitionId", "PublicLeaderboardRank", "PrivateLeaderboardRank"], team_rows)

    out = run(capsys, "--data-dir", str(tmp_path), "--keywords", "eeg", "--metric", "kl", "--shakeup")
    assert len(out["competitions"]) == 1
    comp = out["competitions"][0]
    assert "eeg time-series" in comp["tags"]
    assert comp["shakeup"]["risk"] == "high"


def test_farid_zero_config_and_dual_engine_merge(tmp_path, capsys):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "farid_competitions.yml").write_text(SAMPLE_FARID_YAML, encoding="utf-8")

    # Pure zero-config index mode (uses local fresh cache, zero network calls)
    out = run(capsys, "--cache-dir", str(cache_dir), "--keywords", "essay", "--metric", "qwk", "--solutions")
    assert out["query"]["source"] == "farid"
    assert out["search_strategy"] == "orthogonal_split"  # 1 domain+metric + 1 metric_only
    aes2 = out["competitions"][0]
    assert aes2["teams"] == 2706  # comma "2,706" parsed properly
    assert aes2["github_repos"] == ["https://github.com/example/aes2-3rd-place"]
    assert aes2["shakeup"]["risk"] == "high"
    assert aes2["solution_threads"][0]["title"] == "1st place solution writeup"

    # Merge both engines without duplicating AES 2.0
    data_dir = tmp_path / "meta"
    data_dir.mkdir()
    write_csv(data_dir / "Competitions.csv", HEADER, COMPS)
    write_csv(data_dir / "ForumTopics.csv", TOPIC_HEADER, TOPICS)
    merged = run(
        capsys, "--source", "both", "--data-dir", str(data_dir), "--cache-dir", str(cache_dir),
        "--keywords", "essay", "--metric", "qwk", "--solutions"
    )
    slugs = [c["slug"] for c in merged["competitions"]]
    assert slugs.count("learning-agency-lab-automated-essay-scoring-2") == 1
    merged_aes2 = next(c for c in merged["competitions"] if c["slug"] == "learning-agency-lab-automated-essay-scoring-2")
    assert merged_aes2["source"] == "meta-kaggle+index"
    assert "https://github.com/example/aes2-3rd-place" in merged_aes2["github_repos"]


def test_missing_column_reports_actual_header(tmp_path):
    write_csv(tmp_path / "Competitions.csv", ["Identifier", "Name"], [["1", "x"]])
    try:
        mk.main(["--data-dir", str(tmp_path), "--keywords", "x"])
    except SystemExit as e:
        assert "Columns present" in str(e) and "Identifier" in str(e)
    else:
        raise AssertionError("expected SystemExit")
