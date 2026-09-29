---
license: mit
task_categories:
- text-generation
tags:
- chemistry
- biology
size_categories:
- 10K<n<100K
---

This is a database for nanomaterial synthesis. By fine-tuning the qwen3-14b model, it can extract synthesis steps, synthesis routes, and corresponding product properties (primarily including size, morphology, absorption spectra, and emission spectra) from target paragraphs. This fine-tuning project can be found at https://github.com/ime1452/Synthesis-Properties-Database-for-Nanomaterials.

The database contains two files: dataset.json holds the raw, unprocessed data, while dataset_low_conf_skip-clean.json was simply cleaned and eliminated low-confidence answers.

The structure of the JSON file is as follows: sample_id is the sample number, title is the source literature or DOI number, paragraph is the target paragraph, step_number is the synthesis step number, step_content is the synthesis step content, product_id is the product number, product_name is the product name, route_sequence is the synthesis route, property_name is the property name, value is the property value.

If you find this database helpful, please cite our paper.

DOI: 10.1021/acsnano.6c03070

https://pubs.acs.org/doi/full/10.1021/acsnano.6c03070