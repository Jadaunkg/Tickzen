# build_variation_library.py (FINAL - Component-Based)

import json
import re
import os
from parrot import Parrot
import warnings
import logging

# Setup basic logging for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def build_component_library():
    """
    Uses the Parrot model to generate a library of paraphrased sentence components
    and saves them to a JSON file. This script is designed to be run once, offline.
    """
    warnings.filterwarnings("ignore")
    component_templates = {
    "intro_pe": ["The company's P/E ratios show", "Looking at the earnings multiples reveals", "From a P/E perspective"],
    "intro_ps_pb": ["Meanwhile, other metrics like Price/Sales and Price/Book indicate", "Looking at other valuation angles shows", "In terms of assets and sales"],
    "intro_ev": ["When we look at enterprise-level metrics", "From an enterprise value perspective", "Taking the company's debt and cash into account"],
    "pe_interp_negative": ["an unreliable valuation picture due to negative earnings.", "that P/E ratios are not meaningful for valuation right now.", "that earnings multiples are negative, rendering them ineffective for analysis."],
    "pe_interp_attractive": ["the stock may be attractively priced compared to its earnings.", "an inexpensive valuation relative to its profit generation.", "a potentially undervalued situation based on its earnings power."],
    "pe_interp_moderate": ["the stock is trading at a moderate premium compared to its earnings.", "a reasonable, though not cheap, valuation against its profits.", "a fair valuation, with some growth expectations already built in."],
    "pe_interp_high": ["the stock is trading at a high premium, reflecting strong growth expectations.", "a rich valuation that reflects significant market optimism.", "that investors are paying a premium for its earnings, likely due to high expectations."],
    "pe_trend_strong": ["The significant dip in the Forward P/E hints that analysts anticipate strong earnings improvement over the next year.", "A notable drop in the forward-looking P/E ratio suggests Wall Street expects robust profit growth ahead."],
    "pe_trend_modest": ["The slight dip in the Forward P/E suggests analysts anticipate modest earnings improvement.", "A minor decrease in the Forward P/E points to expectations of moderate earnings growth."],
    "pe_trend_stable": ["The lack of a significant drop in the Forward P/E implies earnings are expected to remain stable or grow only slightly.", "With the Forward P/E not being substantially lower, earnings are projected to be relatively consistent."],
    "ps_pb_analysis_main": ["the stock isn’t cheap relative to its revenue or net assets, but it’s not wildly overvalued either.", "the company presents a balanced picture, suggesting a valuation that is neither deeply discounted nor excessively speculative."],
    "ps_pb_implication": ["These multiples align with a reasonably healthy business, though they leave little room for error if growth slows.", "Such ratios are consistent with a fundamentally sound company, although they imply that strong performance is already expected by the market."],
    "ps_only_analysis": ["investors are paying {ps_ratio_fmt} for every dollar of revenue, a key metric for growth-focused companies.", "its Price/Sales multiple is a critical indicator often used to evaluate growth stocks."],
    "ev_subject_revenue": ["its EV/Revenue ratio", "the company's Enterprise Value-to-Revenue multiple", "the EV/Revenue metric"],
    "ev_subject_ebitda": ["its EV/EBITDA ratio", "the Enterprise Value-to-EBITDA multiple", "the EV/EBITDA metric"],
    "ev_verb": ["shows", "indicates", "points to", "suggests", "reveals"],
    "ev_observation_rev_fair": ["a fair but not bargain valuation for its sales.", "a reasonable valuation based on its revenue stream."],
    "ev_observation_ebitda_reasonable": ["that the enterprise value is well-supported by operational earnings.", "a sensible valuation level against its core profits."],
    "ev_observation_ebitda_stretched": ["an elevated level that could be risky if profit margins contract.", "that it sits at the higher end of the spectrum, which could be a concern if margins come under pressure."],
    "synthesis_conclusion": ["Taken together, these ratios paint a picture of a fairly valued stock where future growth is already priced in. Investors should weigh these multiples against industry peers and historical data to gauge if the current price is justified.", "In summary, these valuation metrics suggest a stock that is reasonably priced, with the market having already factored in expectations for future growth. A deep discount is not apparent, and investors should benchmark these figures against competitors to determine if the valuation is fair."]
}


    logging.info("Loading paraphrasing model... This is a one-time, slow process.")
    try:
        parrot = Parrot(model_tag="prithivida/parrot_paraphraser_on_T5", use_gpu=False)
        logging.info("Model loaded successfully.")
    except Exception as e:
        logging.critical(f"Failed to load parrot model. Aborting. Error: {e}", exc_info=True)
        return

    variation_library = {}
    num_variations_to_generate = 20 

    for key, base_templates in component_templates.items():
        logging.info(f"\nProcessing component key: '{key}'...")
        all_variations_for_this_key = set(base_templates)

        for template in base_templates:
            if re.search(r'({[^{}]+})', template):
                logging.info(f"  - Skipping template with placeholders: \"{template[:70]}...\"")
                continue
            
            logging.info(f"  - Paraphrasing: \"{template[:70]}...\"")
            try:
                para_phrases = parrot.augment(
                    input_phrase=template,
                    adequacy_threshold=0.90,
                    fluency_threshold=0.90,
                    max_return_phrases=num_variations_to_generate
                )
                if para_phrases:
                    for phrase, _ in para_phrases:
                        all_variations_for_this_key.add(phrase.strip())
            except Exception as e:
                logging.error(f"    An error occurred during augmentation for template '{template[:30]}...': {e}")
        
        variation_library[key] = list(all_variations_for_this_key)
        logging.info(f"  --> Generated {len(all_variations_for_this_key)} unique variations for '{key}'.")

    # Corrected output path to be inside the 'app' directory, relative to the project root.
    project_root = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(project_root, 'variation_library.json')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(variation_library, f, indent=4)

    logging.info(f"\nSuccessfully generated and saved component library to: {output_path}")
# ...existing code...

if __name__ == '__main__':
    build_component_library()
