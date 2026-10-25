# Merge the adjudicated documents into trials.csv, dataset.csv and qa/decisions.csv, and print the round numbers for RODADA.md
# Usage: python method/merge.py   (paths are relative to the doencas-feijao folder)
# Copied from ferrugem-soja/method/merge.py. Changed for schema v3: trials.csv, trial vs record errors, and quotes
# longer than 15 words are cut by checking every text field against the PDF text layer, not only quoted spans
import csv
import glob
import json
import os
import re
import subprocess
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_QUOTE_WORDS = 15
COMPARED_RECORD_FIELD_COUNT = 24  # COMPARED_FIELDS in method/compare.py; value also covers value_as_printed
COMPARED_TRIAL_FIELD_COUNT = 13  # TRIAL_FIELDS in method/compare.py
LICENSE_REPOSITORY = "CC BY-NC-ND 4.0 (aviso geral do repositório {repo}, não é licença do item)"

# Free-text fields that may carry copied source text
TRIAL_TEXT_FIELDS = ["trial_label", "inoculation", "application_method", "application_stages", "design_notes", "notes"]
RECORD_TEXT_FIELDS = ["notes", "source_inconsistency", "transformation_stated", "crop_stage"]
DECISION_TEXT_COLUMNS = ["a_value", "b_value", "final_value", "evidence"]

# Quotes: 'x', "x", ‘x’, “x”. The single quote must not touch a letter, so "B's" is not a quote
QUOTE_PATTERN = re.compile(r"(?<![\w])'([^']{3,}?)'(?![\w])|\"([^\"]{3,}?)\"|‘([^’]+)’|“([^”]+)”")

# Decision rows that are not a field of a paired record or trial
TRIAL_TABLE_LABEL = "trials"
CHECKLIST_TABLE_LABEL = "context_checklist"

# Records kept from one side that are optional (text summaries), not counted in the required base
OPTIONAL_RECORDS_KEPT = {"sartorato2003-antracnose-misturas": 1}

# Errors the adjudicators settled outside the field rows of the diff. Each has its line in the per-document summary
# cobucci2006: A wrote statistic_stated false on its 60 Tabela 2 p22 records, which B never transcribed (no pair, no field row)
EXTRA_A_RECORD_ERRORS = {"cobucci2006-area-polo-antracnose": (60, 60)}
# sartorato2006-misturas: the p3 text value is in A and in B but did not pair (A label inferred, B context missing): 1 error each
UNPAIRED_SAME_RECORD = {"sartorato2006-mancha-angular-misturas": 1}

# Trial-context fields of the soybean round, for the cascade comparison (those fields lived on every record there)
SOYBEAN_TRIAL_CONTEXT_FIELDS = {"application_stages", "affiliation", "trial_label", "sowing_date", "location", "n_reps",
	"design_notes", "application_method", "season_or_year"}


def NormalizeWord(word):
	return re.sub(r"^[^\w]+|[^\w]+$", "", word.lower())


def LoadPdfWordShingles(pdf_path):
	# Text layer of the whole PDF, with line-break hyphens joined, as a set of 16-word sequences
	pdf_text = subprocess.run(["pdftotext", "-enc", "UTF-8", pdf_path, "-"], capture_output=True).stdout.decode("utf-8", "replace")
	pdf_text = re.sub(r"-\s*\n\s*", "", pdf_text)
	pdf_words = [NormalizeWord(word) for word in pdf_text.split()]
	pdf_words = [word for word in pdf_words if word]
	shingle_size = MAX_QUOTE_WORDS + 1
	return {tuple(pdf_words[index:index + shingle_size]) for index in range(len(pdf_words) - shingle_size + 1)}


def LongestCopiedRun(text, pdf_shingles):
	# Returns (start, end) word positions of copied runs longer than the limit, on the whitespace-split text
	words = text.split()
	normalized = [NormalizeWord(word) for word in words]
	shingle_size = MAX_QUOTE_WORDS + 1
	runs = []
	index = 0
	while index + shingle_size <= len(words):
		if tuple(normalized[index:index + shingle_size]) in pdf_shingles and "" not in normalized[index:index + shingle_size]:
			run_end = index + shingle_size
			while run_end < len(words) and tuple(normalized[run_end - shingle_size + 1:run_end + 1]) in pdf_shingles:
				run_end += 1
			runs.append((index, run_end))
			index = run_end
		else:
			index += 1
	return runs


def ShortenQuote(match):
	quoted_text = next(group for group in match.groups() if group)
	words = quoted_text.split()
	if len(words) <= MAX_QUOTE_WORDS:
		return match.group(0)
	# Keep the start and the end, where the number usually is
	shortened = " ".join(words[:7]) + " (...) " + " ".join(words[-6:])
	return match.group(0)[0] + shortened + match.group(0)[-1]


def ShortenText(text, pdf_shingles, counter, counter_key):
	if not isinstance(text, str) or not text:
		return text
	new_text = QUOTE_PATTERN.sub(ShortenQuote, text)
	runs = LongestCopiedRun(new_text, pdf_shingles)
	if runs:
		words = new_text.split()
		# Cut from the last run backwards so the positions of the earlier runs stay right
		for run_start, run_end in reversed(runs):
			words[run_start + 7:run_end - 6] = ["(...)"]
		new_text = " ".join(words)
	if new_text != text:
		counter[counter_key] += 1
	return new_text


def BuildCitation(document):
	authors = "; ".join(document["authors"]).rstrip(".")
	title = document["title"].rstrip(".")
	return f"{authors}. {title}. {document['citation']} Disponível em: {document['record_url']}"


def BuildLicense(document):
	license_text = LICENSE_REPOSITORY.format(repo=document["repository"])
	if document.get("publisher_copyright_in_pdf"):
		license_text += "; o PDF imprime: " + document["publisher_copyright_in_pdf"]
	if document.get("journal_article"):
		license_text += "; artigo de periódico, valem os termos da revista (não conferidos)"
	return license_text


def DecisionIds(record):
	ids = record.get("decision_ids")
	if isinstance(ids, list):
		return "; ".join(str(each_id) for each_id in ids)
	return ids or ""


def SideOfError(decision):
	# Which side a decision counts against
	if decision == "B_right":
		return ("A",)
	if decision == "A_right":
		return ("B",)
	if decision == "both_wrong":
		return ("A", "B")
	return ()


def main():
	schema = json.load(open(os.path.join(ROOT, "schema.json"), encoding="utf-8"))
	record_fields = schema["$defs"]["record"]["required"]
	trial_fields = schema["$defs"]["trial"]["required"]
	sources = json.load(open(os.path.join(ROOT, "sources.json"), encoding="utf-8"))
	documents_by_id = {document["id"]: document for document in sources["documents"]}

	shortened = Counter()
	shingles_by_doc = {}
	dataset_rows = []
	trial_rows = []
	stats = defaultdict(dict)
	for adjudicated_path in sorted(glob.glob(os.path.join(ROOT, "adjudicated", "*.json"))):
		doc_id = os.path.basename(adjudicated_path)[:-5]
		document = documents_by_id[doc_id]
		pdf_shingles = LoadPdfWordShingles(os.path.join(ROOT, document["pdf_path"]))
		shingles_by_doc[doc_id] = pdf_shingles
		adjudicated = json.load(open(adjudicated_path, encoding="utf-8"))
		citation, license_text = BuildCitation(document), BuildLicense(document)
		trial_ids = set()
		for trial in adjudicated["trials"]:
			assert all(field in trial for field in trial_fields), (doc_id, trial.get("trial_id"))
			row = {"doc_id": doc_id}
			for field in trial_fields:
				value = trial[field]
				if field == "context_source_pages":
					value = json.dumps(value, ensure_ascii=False) if value else ""
				elif field in TRIAL_TEXT_FIELDS:
					value = ShortenText(value, pdf_shingles, shortened, "trials." + field)
				row[field] = value
			row["citation"] = citation
			trial_rows.append(row)
			trial_ids.add(trial["trial_id"])
		for record_number, record in enumerate(adjudicated["records"], start=1):
			# Every schema field must be there, the record belongs to this document and points to one of its trials
			assert all(field in record for field in record_fields), (doc_id, record_number)
			assert record["doc_id"] == doc_id
			assert record["trial_id"] in trial_ids, (doc_id, record_number, record["trial_id"])
			row = {"record_id": f"{doc_id}#{record_number:04d}"}
			for field in record_fields:
				value = record[field]
				if field in RECORD_TEXT_FIELDS:
					value = ShortenText(value, pdf_shingles, shortened, "records." + field)
				row[field] = value
			row["origin"] = record.get("origin")
			row["decision_ids"] = DecisionIds(record)
			row["citation"] = citation
			row["license"] = license_text
			dataset_rows.append(row)
		stats[doc_id]["final"] = len(adjudicated["records"])
		stats[doc_id]["trials"] = len(adjudicated["trials"])

	# trial_id is per document (t1, t2...), so the dataset joins trials.csv on doc_id + trial_id
	record_columns = ["record_id", "doc_id", "trial_id"] + [field for field in record_fields if field not in ("doc_id", "trial_id")]
	record_columns += ["origin", "decision_ids", "citation", "license"]
	with open(os.path.join(ROOT, "dataset.csv"), "w", encoding="utf-8", newline="") as output_file:
		writer = csv.DictWriter(output_file, fieldnames=record_columns)
		writer.writeheader()
		for row in dataset_rows:
			writer.writerow({key: ("" if value is None else value) for key, value in row.items()})
	trial_columns = ["doc_id"] + trial_fields + ["citation"]
	with open(os.path.join(ROOT, "trials.csv"), "w", encoding="utf-8", newline="") as output_file:
		writer = csv.DictWriter(output_file, fieldnames=trial_columns)
		writer.writeheader()
		for row in trial_rows:
			writer.writerow({key: ("" if value is None else value) for key, value in row.items()})

	# Concatenate the decision files, union of columns, evidence quotes cut like the notes
	decision_rows = []
	decision_columns = ["source_file"]
	for decisions_path in sorted(glob.glob(os.path.join(ROOT, "adjudicated", "*_decisions.csv"))):
		for row in csv.DictReader(open(decisions_path, encoding="utf-8-sig", newline="")):
			row["source_file"] = "adjudicated/" + os.path.basename(decisions_path)
			for column in DECISION_TEXT_COLUMNS:
				row[column] = ShortenText(row.get(column), shingles_by_doc[row["doc_id"]], shortened, "decisions." + column)
			for key in row:
				if key not in decision_columns:
					decision_columns.append(key)
			decision_rows.append(row)
	os.makedirs(os.path.join(ROOT, "qa"), exist_ok=True)
	with open(os.path.join(ROOT, "qa", "decisions.csv"), "w", encoding="utf-8", newline="") as output_file:
		writer = csv.DictWriter(output_file, fieldnames=decision_columns)
		writer.writeheader()
		writer.writerows(decision_rows)

	# Per side: trial field errors, record field errors, records with a wrong field, omissions, checklist and inventory
	field_errors_by_side = Counter()
	real_divergence_pairs = set()
	for doc_id in stats:
		a_document = json.load(open(os.path.join(ROOT, "A", doc_id + ".json"), encoding="utf-8"))
		b_document = json.load(open(os.path.join(ROOT, "B", doc_id + ".json"), encoding="utf-8"))
		doc_stats = stats[doc_id]
		doc_stats.update(a_records=len(a_document["records"]), b_records=len(b_document["records"]),
			a_trials=len(a_document["trials"]), b_trials=len(b_document["trials"]))
		counts = Counter()
		wrong_records = {"A": set(), "B": set()}
		wrong_trials = {"A": set(), "B": set()}
		wrong_fields_by_record = {"A": defaultdict(set), "B": defaultdict(set)}
		for row in decision_rows:
			if row["doc_id"] != doc_id:
				continue
			counts["diff_rows"] += 1
			counts["decision_" + row["decision"]] += 1
			kind, field, table_label = row["kind"], row["field"], row["table_or_figure"]
			sides = SideOfError(row["decision"])
			if kind.startswith("only_in"):
				# Missing on the other side when settled for the side that has it; extra record or trial otherwise
				present_side = kind[-1]
				missing_side = "B" if present_side == "A" else "A"
				unit = "trial" if field == "trial" else "record"
				if doc_id in UNPAIRED_SAME_RECORD:
					continue
				if doc_id in OPTIONAL_RECORDS_KEPT:
					counts[f"{present_side}_{unit}_optional"] += 1
					continue
				if row["decision"] in (present_side + "_right", "ambiguous_print"):
					counts[f"{missing_side}_{unit}_omitted"] += 1
				elif row["decision"] == missing_side + "_right":
					counts[f"{present_side}_{unit}_spurious"] += 1
				else:
					counts[f"{present_side}_{unit}_optional"] += 1
				continue
			if field.startswith("tables") or kind.startswith("inventory"):
				for side in sides:
					counts[side + "_inventory_errors"] += 1
				continue
			if table_label == CHECKLIST_TABLE_LABEL:
				for side in sides:
					counts[side + "_checklist_errors"] += 1
				continue
			if table_label == TRIAL_TABLE_LABEL:
				for side in sides:
					counts[side + "_trial_field_errors"] += 1
					wrong_trials[side].add(row[side.lower() + "_index"])
					field_errors_by_side[(side, "trial." + field)] += 1
				continue
			counts["record_diff_rows"] += 1
			for side in sides:
				counts[side + "_record_field_errors"] += 1
				wrong_records[side].add(row[side.lower() + "_index"])
				wrong_fields_by_record[side][row[side.lower() + "_index"]].add(field)
				field_errors_by_side[(side, field)] += 1
			if sides:
				counts["pairs_with_real_divergence_rows"] += 1
				real_divergence_pairs.add((doc_id, row["a_index"], row["b_index"]))
		extra_fields, extra_records = EXTRA_A_RECORD_ERRORS.get(doc_id, (0, 0))
		counts["A_record_field_errors"] += extra_fields
		unpaired = UNPAIRED_SAME_RECORD.get(doc_id, 0)
		counts["A_record_field_errors"] += unpaired
		counts["B_record_field_errors"] += unpaired
		doc_stats.update(counts)
		doc_stats["A_wrong_records"] = len(wrong_records["A"]) + extra_records + unpaired
		doc_stats["B_wrong_records"] = len(wrong_records["B"]) + unpaired
		for side in ("A", "B"):
			doc_stats[side + "_wrong_records_only_statistic_stated"] = sum(1 for fields in wrong_fields_by_record[side].values() if fields == {"statistic_stated"})
		# The cobucci2006 p22 records of A have statistic_stated as their only wrong field
		doc_stats["A_wrong_records_only_statistic_stated"] += extra_records
		doc_stats["A_wrong_trials"] = len(wrong_trials["A"])
		doc_stats["B_wrong_trials"] = len(wrong_trials["B"])
		doc_stats["required"] = doc_stats["final"] - OPTIONAL_RECORDS_KEPT.get(doc_id, 0)

	totals = Counter()
	print("doc_id;final;trials;A_rec;B_rec;A_rec_err_fields;B_rec_err_fields;A_wrong_rec;B_wrong_rec;A_omit;B_omit;A_trial_err;B_trial_err;B_trial_omit")
	for doc_id, doc_stats in sorted(stats.items()):
		for key, value in doc_stats.items():
			totals[key] += value
		print(f"{doc_id};{doc_stats['final']};{doc_stats['trials']};{doc_stats['a_records']};{doc_stats['b_records']};"
			f"{doc_stats.get('A_record_field_errors', 0)};{doc_stats.get('B_record_field_errors', 0)};{doc_stats['A_wrong_records']};"
			f"{doc_stats['B_wrong_records']};{doc_stats.get('A_record_omitted', 0)};{doc_stats.get('B_record_omitted', 0)};"
			f"{doc_stats.get('A_trial_field_errors', 0)};{doc_stats.get('B_trial_field_errors', 0)};{doc_stats.get('B_trial_omitted', 0)}")
	print(dict(sorted(totals.items())))

	# Accuracy per record and per trial, counting omissions, on the required base
	required = totals["required"]
	for side in ("A", "B"):
		omitted = totals[side + "_record_omitted"]
		wrong = totals[side + "_wrong_records"]
		print(f"{side} records: right {required - omitted - wrong}/{required} = {100 * (required - omitted - wrong) / required:.1f}%"
			f" | omitted {omitted} | with error {wrong} | spurious {totals[side + '_record_spurious']}")
		paired = required - omitted
		field_errors = totals[side + "_record_field_errors"]
		print(f"{side} record fields: {field_errors}/{paired * COMPARED_RECORD_FIELD_COUNT} wrong = {100 * field_errors / (paired * COMPARED_RECORD_FIELD_COUNT):.2f}%")
		trial_total = totals["trials"]
		trial_omitted = totals[side + "_trial_omitted"]
		wrong_trials = totals[side + "_wrong_trials"]
		trial_field_errors = totals[side + "_trial_field_errors"]
		trial_fields_compared = (trial_total - trial_omitted) * COMPARED_TRIAL_FIELD_COUNT
		print(f"{side} trials: right {trial_total - trial_omitted - wrong_trials}/{trial_total} | omitted {trial_omitted} | with error {wrong_trials}"
			f" | trial fields wrong {trial_field_errors}/{trial_fields_compared} = {100 * trial_field_errors / trial_fields_compared:.2f}%"
			f" | checklist errors {totals[side + '_checklist_errors']} | inventory errors {totals[side + '_inventory_errors']}")
	print("pairs with a real divergence:", len(real_divergence_pairs))
	print("field errors by side:", sorted(field_errors_by_side.items(), key=lambda item: -item[1]))

	# Value agreement: any decision row on value, value_as_printed, significance_letter or unit that is not wording
	value_rows = [row for row in decision_rows if row["field"] in ("value", "value_as_printed", "significance_letter", "unit")]
	print("value/letter/unit diff rows:", Counter((row["doc_id"][:20], row["field"], row["decision"]) for row in value_rows))
	print("shortened:", dict(shortened))
	print("decision rows:", len(decision_rows), Counter(row["decision"] for row in decision_rows))
	print("origin:", Counter(row["origin"] for row in dataset_rows))
	print("variable_standardized:", Counter(row["variable_standardized"] for row in dataset_rows).most_common())
	print("other by doc:", Counter(row["doc_id"] for row in dataset_rows if row["variable_standardized"] == "other"))
	print("disease:", Counter(row["disease"] for row in dataset_rows).most_common())
	print("treatment_type:", Counter(row["treatment_type"] for row in dataset_rows).most_common())
	print("statistic:", Counter(row["statistic"] for row in dataset_rows).most_common())
	print("value_kind:", Counter(row["value_kind"] for row in dataset_rows).most_common())
	for field in ("cultivar", "dose_and_unit", "application_stages", "crop_stage", "significance_letter", "active_ingredient_or_agent"):
		empty = sum(1 for row in dataset_rows if row[field] in (None, ""))
		print(f"null record {field}: {empty} ({100 * empty / len(dataset_rows):.1f}%)")
	for field in ("location", "affiliation", "season_or_year", "sowing_date", "cultivar", "inoculation", "application_method", "application_stages", "n_reps"):
		empty = sum(1 for row in trial_rows if row[field] in (None, ""))
		print(f"null trial {field}: {empty}/{len(trial_rows)}")
	print("environment:", Counter(row["environment"] for row in trial_rows))
	print("source_inconsistency filled:", sum(1 for row in dataset_rows if row["source_inconsistency"]))
	print("from text:", sum(1 for row in dataset_rows if row["table_or_figure"] == "text"))
	print("empty decision_ids:", Counter(row["doc_id"] for row in dataset_rows if not row["decision_ids"]))

	# Soybean round, same split: errors in fields that this round moved to trials[]
	soybean_path = os.path.join(ROOT, "..", "ferrugem-soja", "qa", "decisions.csv")
	soybean_errors = Counter()
	for row in csv.DictReader(open(soybean_path, encoding="utf-8")):
		for side in SideOfError(row["decision"]):
			group = "trial_context" if row["field"] in SOYBEAN_TRIAL_CONTEXT_FIELDS else "other"
			soybean_errors[(side, group)] += 1
	print("soybean errors by group:", dict(soybean_errors))

	# Self-check: every adjudicated record once, every record points to a trial, and no copied run over the limit is left
	assert len(dataset_rows) == sum(doc_stats["final"] for doc_stats in stats.values())
	assert len({row["record_id"] for row in dataset_rows}) == len(dataset_rows)
	assert len({(row["doc_id"], row["trial_id"]) for row in trial_rows}) == len(trial_rows)
	trial_keys = {(row["doc_id"], row["trial_id"]) for row in trial_rows}
	assert all((row["doc_id"], row["trial_id"]) in trial_keys for row in dataset_rows)
	for row in dataset_rows:
		for field in RECORD_TEXT_FIELDS:
			if isinstance(row[field], str):
				assert not LongestCopiedRun(row[field], shingles_by_doc[row["doc_id"]]), (row["record_id"], field)
				for match in QUOTE_PATTERN.finditer(row[field]):
					assert len(next(group for group in match.groups() if group).split()) <= MAX_QUOTE_WORDS
	for row in trial_rows:
		for field in TRIAL_TEXT_FIELDS:
			if isinstance(row[field], str):
				assert not LongestCopiedRun(row[field], shingles_by_doc[row["doc_id"]]), (row["doc_id"], row["trial_id"], field)
	for row in decision_rows:
		assert not LongestCopiedRun(row.get("evidence") or "", shingles_by_doc[row["doc_id"]]), row["diff_id"]
	# The cut itself: a 20-word copy becomes 7 words, (...), 6 words
	test_words = [f"w{index}" for index in range(20)]
	test_shingles = {tuple(test_words[index:index + MAX_QUOTE_WORDS + 1]) for index in range(5)}
	assert ShortenText(" ".join(test_words), test_shingles, Counter(), "test").split() == test_words[:7] + ["(...)"] + test_words[-6:]


if __name__ == "__main__":
	main()
