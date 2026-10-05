# def get_entity_in_full_wikibase_api_format(self):
#     pass
# terms_repo = TermsRepository(vitess_client.connection_manager)

# Load metadata from Vitess/S3
# if fetch_metadata:
#     # Reconstruct labels from per-language hashes (Vitess)
#     labels_hashes = revision.content.get("labels_hashes", {})
#     if labels_hashes:
#         data["labels"] = {}
#         for lang, hash_value in labels_hashes.items():
#             label_value = terms_repo.get_term(hash_value)
#             if label_value is not None:
#                 data["labels"][lang] = {
#                     "language": lang,
#                     "value": label_value,
#                 }
#
#     # Reconstruct descriptions from per-language hashes (S3)
#     descriptions_hashes = revision.content.get("descriptions_hashes", {})
#     if descriptions_hashes:
#         data["descriptions"] = {}
#         for lang, hash_value in descriptions_hashes.items():
#             desc_value = s3_client.load_metadata("descriptions", hash_value)
#             data["descriptions"][lang] = {
#                 "language": lang,
#                 "value": desc_value,
#             }
#
#     # Reconstruct aliases from per-language hash arrays (Vitess)
#     aliases_hashes = revision.content.get("aliases_hashes", {})
#     if aliases_hashes:
#         data["aliases"] = {}
#         for lang, hash_list in aliases_hashes.items():
#             data["aliases"][lang] = []
#             for hash_value in hash_list:
#                 alias_value = terms_repo.get_term(hash_value)
#                 if alias_value is not None:
#                     data["aliases"][lang].append(
#                         {"language": lang, "value": alias_value}
#                     )
# else:
#     # For legacy compatibility, merge metadata into entity data
#     entity_data = data["entity"]
#     labels_hashes = revision.content.get("labels_hashes", {})
#     if labels_hashes:
#         entity_data["labels"] = {}
#         for lang, hash_value in labels_hashes.items():
#             label_value = terms_repo.get_term(hash_value)
#             if label_value is not None:
#                 entity_data["labels"][lang] = {
#                     "language": lang,
#                     "value": label_value,
#                 }
#
#     descriptions_hashes = revision.content.get("descriptions_hashes", {})
#     if descriptions_hashes:
#         entity_data["descriptions"] = {}
#         for lang, hash_value in descriptions_hashes.items():
#             desc_value = s3_client.load_metadata("descriptions", hash_value)
#             entity_data["descriptions"][lang] = {
#                 "language": lang,
#                 "value": desc_value,
#             }
#
#     aliases_hashes = revision.content.get("aliases_hashes", {})
#     if aliases_hashes:
#         entity_data["aliases"] = {}
#         for lang, hash_list in aliases_hashes.items():
#             entity_data["aliases"][lang] = []
#             for hash_value in hash_list:
#                 alias_value = terms_repo.get_term(hash_value)
#                 if alias_value is not None:
#                     entity_data["aliases"][lang].append(
#                         {"language": lang, "value": alias_value}
#                     )
