#!/usr/bin/env python3
"""
Canonical GYTS / GATS indicator vocabularies, used to normalise the raw
(possibly layout-mangled) labels that gtss_extract.py pulls out of fact-sheet
PDFs. Built from a fully clean extraction (Ghana 2017 GYTS, Ethiopia 2024
GATS) that matches the official WHO fact-sheet wording.

Each entry: (code, canonical_label, section_code, section_name)
"""

GYTS_INDICATORS = [
    ("gyts_current_tobacco_smokers",       "Current tobacco smokers",                                                                    "SMOKED",  "Smoked Tobacco"),
    ("gyts_current_cigarette_smokers",     "Current cigarette smokers",                                                                  "SMOKED",  "Smoked Tobacco"),
    ("gyts_frequent_cigarette_smokers",    "Frequent cigarette smokers",                                                                 "SMOKED",  "Smoked Tobacco"),
    ("gyts_current_other_tobacco",         "Current smokers of other tobacco",                                                           "SMOKED",  "Smoked Tobacco"),
    ("gyts_current_shisha",                "Current shisha smokers",                                                                     "SMOKED",  "Smoked Tobacco"),
    ("gyts_ever_tobacco_smokers",          "Ever tobacco smokers",                                                                       "SMOKED",  "Smoked Tobacco"),
    ("gyts_ever_cigarette_smokers",        "Ever cigarette smokers",                                                                     "SMOKED",  "Smoked Tobacco"),
    ("gyts_ever_other_tobacco",            "Ever smokers of other tobacco",                                                              "SMOKED",  "Smoked Tobacco"),
    ("gyts_ever_shisha",                   "Ever shisha smokers",                                                                        "SMOKED",  "Smoked Tobacco"),
    ("gyts_current_smokeless",             "Current smokeless tobacco users",                                                            "SMOKELESS", "Smokeless Tobacco"),
    ("gyts_ever_smokeless",                "Ever smokeless tobacco users",                                                               "SMOKELESS", "Smokeless Tobacco"),
    ("gyts_current_any_tobacco",           "Current tobacco users",                                                                      "ANY",     "Any Tobacco Use"),
    ("gyts_ever_any_tobacco",              "Ever tobacco users",                                                                         "ANY",     "Any Tobacco Use"),
    ("gyts_susceptible_future_use",        "Never tobacco users susceptible to tobacco use in the future",                              "SUSCEPT", "Susceptibility"),
    ("gyts_susceptible_enjoy_cigarette",   "Never tobacco smokers who thought they might enjoy smoking a cigarette",                    "SUSCEPT", "Susceptibility"),
    ("gyts_current_ecig",                  "Current electronic cigarette users",                                                         "ECIG",    "Electronic Cigarettes"),
    ("gyts_ever_ecig",                     "Ever electronic cigarette users",                                                            "ECIG",    "Electronic Cigarettes"),
    ("gyts_tried_to_stop",                 "Current tobacco smokers who tried to stop smoking in the past 12 months",                   "CESSATION", "Cessation"),
    ("gyts_wanted_to_stop_now",            "Current tobacco smokers who wanted to stop smoking now",                                    "CESSATION", "Cessation"),
    ("gyts_thought_could_stop",            "Current tobacco smokers who thought they would be able to stop smoking if they wanted to",  "CESSATION", "Cessation"),
    ("gyts_received_help_to_stop",         "Current tobacco smokers who have ever received help/advice from a program or professional to stop smoking", "CESSATION", "Cessation"),
    ("gyts_shs_home",                      "Exposure to tobacco smoke at home",                                                          "SHS",     "Secondhand Smoke"),
    ("gyts_shs_enclosed_public",           "Exposure to tobacco smoke inside any enclosed public place",                                "SHS",     "Secondhand Smoke"),
    ("gyts_shs_outdoor_public",            "Exposure to tobacco smoke at any outdoor public place",                                     "SHS",     "Secondhand Smoke"),
    ("gyts_saw_smoking_at_school",         "Students who saw anyone smoking inside the school building or outside on school property",  "SHS",     "Secondhand Smoke"),
    ("gyts_bought_from_store",             "Current cigarette smokers who bought cigarettes from a store, shop, street vendor, or kiosk", "ACCESS",  "Access & Availability"),
    ("gyts_not_prevented_by_age",          "Current cigarette smokers who were not prevented from buying cigarettes because of their age", "ACCESS",  "Access & Availability"),
    ("gyts_bought_individual_sticks",      "Current cigarette smokers who bought cigarettes as individual sticks",                      "ACCESS",  "Access & Availability"),
    ("gyts_noticed_ads_pos",               "Students who noticed tobacco advertisements or promotions at points of sale",               "ADVERT",  "Tobacco Advertising"),
    ("gyts_saw_tobacco_on_media",          "Students who saw anyone using tobacco on television, videos, or movies",                    "ADVERT",  "Tobacco Advertising"),
    ("gyts_offered_free_product",          "Students who were ever offered a free tobacco product from a tobacco company representative", "ADVERT",  "Tobacco Advertising"),
    ("gyts_had_branded_item",              "Students who had something with a tobacco brand logo on it",                                "ADVERT",  "Tobacco Advertising"),
    ("gyts_noticed_antitobacco_media",     "Students who noticed anti-tobacco messages in the media",                                   "ADVERT",  "Tobacco Advertising"),
    ("gyts_noticed_antitobacco_events",    "Students who noticed anti-tobacco messages at sporting or community events",                "ADVERT",  "Tobacco Advertising"),
    ("gyts_thought_quit_warning_label",    "Current tobacco smokers who thought about quitting because of a warning label",             "ADVERT",  "Tobacco Advertising"),
    ("gyts_taught_dangers_school",         "Students who were taught in school about the dangers of tobacco use in the past 12 months",  "ADVERT",  "Tobacco Advertising"),
    ("gyts_think_difficult_quit",          "Students who definitely thought it is difficult to quit once someone starts smoking tobacco", "KNOW",  "Knowledge & Attitudes"),
    ("gyts_think_smoking_helps_social",    "Students who thought smoking tobacco helps people feel more comfortable at celebrations, parties, and social gatherings", "KNOW", "Knowledge & Attitudes"),
    ("gyts_think_smoking_harmful_others",  "Students who definitely thought other people's tobacco smoking is harmful to them",         "KNOW",    "Knowledge & Attitudes"),
    ("gyts_favor_ban_enclosed",            "Students who favored prohibiting smoking inside enclosed public places",                    "KNOW",    "Knowledge & Attitudes"),
    ("gyts_favor_ban_outdoor",             "Students who favored prohibiting smoking at outdoor public places",                         "KNOW",    "Knowledge & Attitudes"),
]

GATS_INDICATORS = [
    ("gats_current_tobacco_users",         "Current tobacco users",                                                                      "USE",     "Tobacco & E-Cigarette Use"),
    ("gats_current_tobacco_smokers",       "Current tobacco smokers",                                                                    "SMOKING", "Tobacco Smoking"),
    ("gats_daily_tobacco_smokers",         "Daily tobacco smokers",                                                                      "SMOKING", "Tobacco Smoking"),
    ("gats_current_cigarette_smokers",     "Current cigarette smokers",                                                                  "SMOKING", "Tobacco Smoking"),
    ("gats_daily_cigarette_smokers",       "Daily cigarette smokers",                                                                    "SMOKING", "Tobacco Smoking"),
    ("gats_former_daily_all_adults",       "Former daily tobacco smokers (among all adults)",                                            "SMOKING", "Tobacco Smoking"),
    ("gats_former_daily_ever_daily",       "Former daily tobacco smokers (among ever daily smokers)",                                    "SMOKING", "Tobacco Smoking"),
    ("gats_current_smokeless",             "Current smokeless tobacco users",                                                            "SMOKELESS", "Smokeless Tobacco Use"),
    ("gats_heard_heated_tobacco",          "Ever heard of heated tobacco products",                                                      "HEATED",  "Heated Tobacco Products"),
    ("gats_ever_heated_tobacco",           "Ever used heated tobacco products",                                                          "HEATED",  "Heated Tobacco Products"),
    ("gats_current_heated_tobacco",        "Current user of heated tobacco products",                                                    "HEATED",  "Heated Tobacco Products"),
    ("gats_heard_ecig",                    "Ever heard of electronic cigarettes",                                                        "ECIG",    "Electronic Cigarettes"),
    ("gats_ever_ecig",                     "Ever used electronic cigarettes",                                                            "ECIG",    "Electronic Cigarettes"),
    ("gats_current_ecig",                  "Current user of electronic cigarettes",                                                      "ECIG",    "Electronic Cigarettes"),
    ("gats_smokers_quit_attempt",          "Smokers who made a quit attempt in past 12 months",                                          "CESSATION", "Cessation"),
    ("gats_smokers_planning_quit",         "Current smokers who planned to or were thinking about quitting",                             "CESSATION", "Cessation"),
    ("gats_smokers_advised_quit",          "Smokers advised to quit by a health care provider in past 12 months",                        "CESSATION", "Cessation"),
    ("gats_smokeless_quit_attempt",        "Smokeless users who made a quit attempt in past 12 months",                                  "CESSATION", "Cessation"),
    ("gats_smokeless_planning_quit",       "Current smokeless users who planned to or were thinking about quitting",                     "CESSATION", "Cessation"),
    ("gats_exposed_workplace",             "Adults exposed to tobacco smoke at the workplace",                                           "SHS",     "Secondhand Smoke"),
    ("gats_exposed_home",                  "Adults exposed to tobacco smoke at home at least monthly",                                   "SHS",     "Secondhand Smoke"),
    ("gats_exposed_govt_buildings",        "Government buildings or offices",                                                            "SHS",     "Secondhand Smoke (Public Places)"),
    ("gats_exposed_healthcare",            "Healthcare facilities",                                                                      "SHS",     "Secondhand Smoke (Public Places)"),
    ("gats_exposed_restaurants",           "Restaurants",                                                                                "SHS",     "Secondhand Smoke (Public Places)"),
    ("gats_exposed_bars",                  "Bars or night clubs",                                                                        "SHS",     "Secondhand Smoke (Public Places)"),
    ("gats_exposed_public_transport",      "Public Transportation",                                                                      "SHS",     "Secondhand Smoke (Public Places)"),
    ("gats_smokers_warning_label",         "Current smokers who thought about quitting because of a warning label",                     "MEDIA",   "Media & Warning Labels"),
    ("gats_smokeless_warning_label",       "Current smokeless tobacco users who thought about quitting because of a warning label",     "MEDIA",   "Media & Warning Labels"),
    ("gats_noticed_ads_stores",            "Adults who noticed any tobacco products (smoked and/or smokeless) advertising or promotions in stores/shops where tobacco is sold", "MEDIA", "Media & Warning Labels"),
    ("gats_noticed_ads_sponsorship",       "Adults who noticed any tobacco products (smoked and/or smokeless) advertisements, promotions, or sporting event sponsorship", "MEDIA", "Media & Warning Labels"),
    ("gats_belief_smoking_illness",        "Adults who believed smoking causes serious illness",                                        "KNOW",    "Knowledge & Attitudes"),
    ("gats_belief_shs_illness",            "Adults who believed breathing other peoples' smoke causes serious illness in nonsmokers",   "KNOW",    "Knowledge & Attitudes"),
    ("gats_belief_smokeless_illness",      "Adults who believed smokeless tobacco use causes serious illness",                          "KNOW",    "Knowledge & Attitudes"),
]


def _words(label):
    return set(w.lower() for w in label.replace(",", " ").replace("(", " ").replace(")", " ").split() if len(w) > 2)


def best_match(fragment_label, canonical_list, min_score=0.42):
    """Return (code, canonical_label, section_code, section_name, score) for the
    best Jaccard word-overlap match, or None if nothing clears min_score."""
    frag_words = _words(fragment_label)
    if not frag_words:
        return None
    best = None
    best_score = 0.0
    for code, label, sec_code, sec_name in canonical_list:
        cand_words = _words(label)
        inter = frag_words & cand_words
        union = frag_words | cand_words
        score = len(inter) / len(union) if union else 0.0
        # Bonus: reward matches that cover most of the (usually short/clean)
        # canonical label even if the fragment carries extra noise words.
        coverage = len(inter) / len(cand_words) if cand_words else 0.0
        combined = 0.5 * score + 0.5 * coverage
        if combined > best_score:
            best_score = combined
            best = (code, label, sec_code, sec_name)
    if best and best_score >= min_score:
        return best + (round(best_score, 3),)
    return None
