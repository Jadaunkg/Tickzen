"""
Gemini Article Generation Testing Script
Uses enhanced search content as context to generate human-like sports articles
Focused on natural writing style with comprehensive coverage from multiple sources
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path to import utilities
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  google-generativeai not installed. Run: pip install google-generativeai")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class GeminiArticleTester:
    """Test Gemini AI for generating human-like sports articles from enhanced search content"""
    
    def __init__(self):
        """Initialize the Gemini Article tester"""
        self.testing_output_dir = Path(__file__).parent / "testing_output"
        self.final_article_dir = Path(__file__).parent / "final_article"
        self.final_article_dir.mkdir(exist_ok=True)
        
        # Configure Gemini
        self.api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            print("❌ ERROR: GEMINI_API_KEY environment variable not found!")
            print("   Please add it to your .env file or set it as an environment variable")
            self.available = False
            return
        
        if not GEMINI_AVAILABLE:
            print("❌ ERROR: Gemini library not available!")
            self.available = False
            return
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Model configuration for human-like writing
        self.generation_config = {
            "temperature": 0.8,  # Higher for more natural variation
            "top_p": 0.9,       # Good balance for creativity
            "top_k": 40,        # Moderate diversity
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        
        # Initialize model (use available model from the list)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",  # Available model from the list
            generation_config=self.generation_config,
        )
        
        self.available = True
        print("✅ Gemini AI configured and ready for article generation")
    
    def generate_human_article_from_sources(self, research_data: Dict) -> Dict:
        """
        Generate a human-like article from enhanced search research data
        
        Args:
            research_data (dict): Enhanced search results with multiple sources
            
        Returns:
            dict: Generated article with metadata
        """
        if not self.available:
            return {
                'status': 'error',
                'error': 'Gemini AI not available'
            }
        
        try:
            print(f"\n🤖 Generating Human-Style Article with Gemini AI")
            print(f"   📊 Processing data from {research_data.get('total_sources_processed', 0)} sources")
            print("="*70)
            
            # Build comprehensive context from all sources
            context = self._build_comprehensive_context(research_data)
            
            # Create human-focused prompt
            prompt = self._build_human_article_prompt(research_data.get('headline', ''), context)
            
            print(f"🚀 Sending request to Gemini...")
            start_time = time.time()
            
            # Generate article
            response = self.model.generate_content(prompt)
            
            generation_time = round(time.time() - start_time, 2)
            
            if response.text:
                article_text = response.text.strip()
                word_count = len(article_text.split())
                
                print(f"✅ Article generated successfully!")
                print(f"   ⏱️  Generation time: {generation_time}s")
                print(f"   📝 Word count: {word_count}")
                print(f"   📊 Coverage: {len(research_data.get('article_contents', []))} sources analyzed")
                
                return {
                    'status': 'success',
                    'article_text': article_text,
                    'word_count': word_count,
                    'generation_time': generation_time,
                    'sources_analyzed': research_data.get('total_sources_processed', 0),
                    'total_source_words': research_data.get('total_words_collected', 0),
                    'headline': research_data.get('headline', ''),
                    'timestamp': datetime.now().isoformat(),
                    'model_used': 'gemini-2.5-flash',
                    'generation_config': self.generation_config
                }
            else:
                print(f"❌ No content generated")
                return {
                    'status': 'error',
                    'error': 'No content generated by Gemini'
                }
                
        except Exception as e:
            print(f"❌ Error generating article: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _build_comprehensive_context(self, research_data: Dict) -> str:
        """Build comprehensive context from all sources"""
        context_parts = []
        
        # Add headline and basic info
        headline = research_data.get('headline', '')
        context_parts.append(f"TOPIC: {headline}")
        
        # Add source information
        total_sources = research_data.get('total_sources_processed', 0)
        total_words = research_data.get('total_words_collected', 0)
        context_parts.append(f"TOTAL SOURCES: {total_sources}")
        context_parts.append(f"TOTAL WORDS: {total_words}")
        
        # Add the combined content directly (this contains all source information)
        combined_content = research_data.get('combined_content', '')
        if combined_content:
            context_parts.append(f"\nCOMBINED SOURCE CONTENT:")
            context_parts.append(combined_content)
        
        # Add content summary for additional context
        content_summary = research_data.get('content_summary', '')
        if content_summary:
            context_parts.append(f"\nCONTENT SUMMARY:")
            context_parts.append(content_summary)
        
        return '\n'.join(context_parts)
    
    def _build_human_article_prompt(self, headline: str, context: str) -> str:
        """Build prompt for human-like article generation using sample articles for style"""
        
        # Placeholder for sample articles (to be filled manually)
        sample_article_1 = """
SAMPLE ARTICLE 1 PLACEHOLDER:
[With the January transfer window approaching, Sheffield United's on-loan Nottingham Forest defender Tyler Bindon is facing an uncertain future at Bramall Lane.

Bindon joined Sheffield United on a season-long loan from Nottingham Forest in the summer, with the move initially seeing him reunite with Ruben Selles after working with him previously at Reading.

The 20-year-old had starred under Selles at the Select Car Leasing Stadium, with his impressive performances for the Royals earning him the move to the City Ground in January before he was loaned back to the League One side for the remainder of the season.

Bindon started the Blades' first four games of the season, but he fell out of favour after Chris Wilder returned to the club to replace Selles in September, with the likes of Japhet Tanganga, Ben Mee and Mark McGuinness all being preferred ahead of him.

Given Bindon's lack of game time, it looked certain that his loan deal would be coming to an early end in January, but with his recent emergence in the team complicating the situation, we rounded up all the latest news on his future.

Sheffield United were preparing to make big Tyler Bindon decision in January
Chris Wilder
Bindon is not the only one of Selles' loan signings to have struggled for minutes under Wilder, with fellow defender Ben Godfrey and forward Louie Barry also spending time on the sidelines in recent months.

As FLW exclusively revealed last month, Sheffield United were preparing to terminate the loan deals of Bindon, Godfrey and Barry in January as they look to trim down what is a bloated squad and potentially even make room for new additions.

Wilder confirmed on Friday that Godfrey would be returning to his parent club Atalanta when the window opens, while he also revealed that the Blades were in talks with Aston Villa about cutting Barry's loan short as he continues his recovery from a knee injury that has kept him out since the end of October.

Given how their spells at Bramall Lane have gone, it is no surprise that Godfrey and Barry will be departing in January, and not long ago, it seemed inevitable that Bindon would be following them out of the exit door, but that may no longer be the case.

Tyler Bindon's surprise Sheffield United return raises Bramall Lane exit doubts
Bramall Lane
After starting the 1-0 defeat at Middlesbrough in August, which proved to be Selles' penultimate game in charge, Bindon did not make a single appearance for Sheffield United for over three months.

Despite being left out of the starting line-up, Bindon was regularly included on the bench by Wilder during that time, and he made a return to action when he replaced McGuinness at half time in the 4-0 win over Stoke City earlier this month.

With McGuinness and Mee both unavailable due to injury, Bindon was handed a rare start in the 1-1 draw against Norwich City the following game, but he then found himself back on the bench for the 2-0 defeat at West Bromwich Albion.

However, after Wilder ripped into his players for their performance at The Hawthorns, Bindon was restored to the team for the 3-0 win over Birmingham City on Saturday, and as well as helping his side to a clean sheet, he also opened the scoring in the fifth minute when he headed home Gustavo Hamer's corner.

Chris Wilder speaks out on Tyler Bindon's Sheffield United future as January looms
Chris Wilder
While Wilder has made brutal decisions in cancelling the loan deals of Godfrey and Barry, it seems he is open to Bindon remaining at Sheffield United for the rest of the season.

Speaking after the victory over Birmingham on Saturday, Wilder admitted that he may have made a mistake by dropping Bindon for the defeat at West Brom, and although he refused to provide any guarantees over his future, he hinted that the New Zealand international could be given a run in the team over the festive period.

"He's got a shirt and I know he enjoys it. He's played well today. He did well. I maybe got that selection wrong last week. Maybe I should have gone with Tyler at West Brom, but I didn't," Wilder told The Star.

"You've seen there's a player in there and he's had to bide his time. But he's got an opportunity now and let's see where it goes.

"I’ve not made a decision on it. Tyler’s been excellent around the place, with his attitude. He’s taken his opportunity, and everything’s on the table.

"Let's see what happens [regarding his future]. He's playing and I'm not going to give everything away to Wrexham, but I don't think there's going to be a huge amount of changes to the back four because of the way they've played."]
"""
        
        sample_article_2 = """
SAMPLE ARTICLE 2 PLACEHOLDER:
[




Mark Robins will have one eye on the January transfer window to improve his Stoke City squad, with one area of the pitch requiring more focus than others.

Having narrowly survived relegation last season, Stoke City are much improved this campaign in almost all areas.

Mark Robins took the helm at the bet365 Stadium on January 1st 2025, with the Potters in real danger of falling into League One, with both Steven Schumacher and Narcis Pelach struggling to keep the club afloat.

According to FotMob, Stoke had the second-worst xG (expected goals) conceded record in the EFL Championship last season, behind only Plymouth Argyle, who themselves were relegated.

This campaign, with only one real change in the backline, that being the free signing of veteran full-back Aaron Cresswell from West Ham United, Stoke have maintained the best defensive record in the league, nearly halfway through the season.

Their solid defensive record has played a huge factor in the club occupying a spot in the play-offs for much of the season, despite having recently dropped out after some patchy form, though their efforts in the final third could still be improved.

Divin Mubama's form has dropped off as the season has progressed, with the goals largely drying up for the England youth international, whilst Robert Bozenik, who signed on a free transfer this summer from Portuguese club Boavista, has yet to score for the Potters, and Sam Gallagher's recent return to fitness has also yielded no goals.

Sorba Thomas' form from the left flank has largely kept the Potters in play-off contention, yet he cannot be solely relied upon throughout the entire campaign, and more contributions will have to be made from elsewhere as the season continues.

With the winter window on the horizon, Robins may well have eyes on recruitment in the final third and should be eyeing moves for these two players.

2
Cameron Archer
Cameron Archer Southampton
Cameron Archer was once one of the hottest prospects in the Championship, being courted by almost every club in the division looking to obtain his signature.

His first spell came with Preston North End in January 2022, where he scored seven goals in 20 appearances and was made a part of parent club Aston Villa's plans for the following campaign.

However, he barely featured in the first half of the 2022/23 season, and subsequently joined Middlesbrough on loan for the second half of the campaign, where he scored 11 and grabbed 6 assists in 20 appearances once more, leading to an £18 million switch to then-Premier League side Sheffield United.

Archer scored just four times as the Blades were relegated from the top flight, which led Villa to act upon their buyback clause included in the deal to sell him, bringing him back to the Midlands before once again selling to his current club, Southampton, for £15 million.

The Englishman struggled to cement a place in the Saints' side last season as the club was relegated from the Premier League, and this season he has made 14 appearances but started just five, scoring once.

With Armstrong the preferred choice up top, this has left Archer with limited minutes off the bench, especially since Tonda Eckert took permanent charge on the South Coast, and a move for the former England Under-21 international could be on the cards this January.

Under contract until the summer of 2028, it's unlikely that Southampton would let him leave permanently, with a loan move being a more likely option, which would suit Stoke, who have room for another loan signing.

Southampton have already loaned out Ben Brereton Diaz to Derby County this season, showing their willingness to strike a deal with other teams in the second tier, something Stoke should keep in mind if they choose to move for Archer.

With rumours of a departure for Damion Downs and injury woes for Ross Stewart, whether Southampton would be willing to allow Archer leave - even on loan - is one thing, and to a direct Championship is another, but Stoke should try their luck nonetheless.

1
Joel Piroe
Joel Piroe was the top goalscorer in the Championship last season, hitting 19 goals as Leeds United snatched the title on the final day with a 100-point haul.

The Dutchman has a proven track record of hitting the back of the net in the second tier, with 73 goals and 18 assists in 179 second-tier appearances for both Leeds and Swansea City.

Piroe has found his game-time to be seriously limited following Leeds' promotion to the top flight, despite him ending the season as their top scorer, starting the opening two games and none thereafter, accumulating just 200 minutes of league football this season.

With the form of Dominic Calvert-Lewin proving to be too good to drop, with Lukas Nmecha acting largely as the backup option, this has left Piroe struggling for minutes this campaign.

Whether the Whites would be willing to loan out Piroe for the remainder of the campaign is yet to be seen, but given his goalscoring record and his lack of game time, the 26-year-old will not be short of interest this January.

Leeds have already shown willingness to loan attacking talent out to the Championship this campaign, with Joe Gelhardt currently thriving for Hull City.

Indeed, Piroe has scored more goals against Stoke than any other Championship club, having netted eight against the Potters in his career, so he certainly knows where the net is against the Staffordshire-based outfit.

Whether that form would translate into hitting goals for Stoke is another question, though. Regardless, Stoke should launch an ambitious move for Piroe this winter as they look to force their way into the play-off picture once more.]
"""
        
        sample_article_3 = """
SAMPLE ARTICLE 3 PLACEHOLDER:
[Chelsea join race for Antoine Semenyo! Blues make contact with Bournemouth star's camp over potential £65m January transfer
A. Semenyo
Chelsea

Transfers
Bournemouth

Premier League
Manchester City

Manchester United

Liverpool

Chelsea have become the latest club to express interest in Bournemouth star Antoine Semenyo. The forward is also being chased by Manchester United, Liverpool and Manchester City ahead of the opening of the January transfer window and is expected to leave in a transfer worth £65 million. The Blues have made an initial enquiry for Semenyo as the race for his signature hots up.


‘We will be there’ - Pep Guardiola on Premier League title race
Play Video
AD
AD
Semenyo wanted by Premier League giants
Semenyo has emerged as a top transfer target for a host of Premier League giants this winter. Manchester United are hoping to add the 25-year-old to their ranks in a bid to solve their issues on the left flank, while Manchester City and Liverpool are also in the race. Liverpool have just lost summer signing Alexander Isak to a leg fracture, meaning the Reds may well dip into the transfer marker for a new attacker. Semenyo has been tipped to make a quick decision on his future as clubs queue up to sign the impressive Bournemouth star.

AD
Bournemouth v Burnley - Premier LeagueGetty Images Sport
Chelsea make enquiry
Chelsea may have invested heavily in the summer but the Blues are willing to splash out again in January on Semenyo, according to The Athletic. The Blues have been in touch to make an initial enquiry and could now "accelerate" their plans this winter. Chelsea had initially been willing to wait until the summer to sign a new forward but Semenyo's availability this winter -  due to a release clause that can be activated - appears to have changed the club's transfer plans. Semenyo has eight goals and three assists for Bournemouth so far this season in 16 Premier League outings.

Looking for smarter football bets? Get expert previews, data-driven predictions & winning insights with GOAL Tips on Telegram. Join our growing community now!

AD
Iraola responds to Semenyo exit talk
Bournemouth manager Andoni Iraola has been quizzed on Semenyo's future and says he wants him to stay but knows it may be difficult. He told reporters: "Antoine Semenyo right now is with us. He has trained today with us, very well. I understand that there is a lot of noise around Antoine. But my concern is that it doesn't affect him, his performances and we are seeing that it is not affecting his performances. He is very committed to the team and I hope we can keep him there. There are situations that we cannot control, but right now, Antoine is our player and he's going to continue playing for us. If you ask me, I don't want to lose him, definitely don't want to lose him. But like we always say, every time the market opens, you never know what's going to happen."

Iraola also highlighted Semenyo's importance to Bournemouth, adding: "Antoine, for me, has been performing very well. Not just the last two games because he has scored. The level of consistency has been very good since the beginning of the season. He has had moments where he hasn't scored and has still been very valuable for us. At the end, we demand not only the numbers, but he gives us a lot of things. It's no secret he is a massive player for us." 
All signs are now pointing to Semenyo leaving Bournemouth in January and moving on, although fans will have to wait and see which club wins the race for his signature. Semenyo has spoken about his future recently but didn't seem too fazed by the speculation. He told Sky Sports: "I don't think about it too much. I try to stay present as much as I can. You see the news all the time, I see it as well, I'm not oblivious, but I try to keep focused. I'm enjoying my football here. If I'm not scoring goals, all of that goes away. I try to stay present, do the best I can for the team, score goals and whatever happens in the future happens."

Bournemouth are due to finish off 2025 with Premier League games against Brentford and Chelsea before the transfer window opens on January 1.  The games could potentially be Semenyo's last in a Bournemouth shirt if he does indeed make a quick decision on his future.]
"""
        
        prompt = f"""Write a sports news article about: {headline}

Use this research: {context}

Style samples (learn writing patterns only, don't copy content):
{sample_article_1}
{sample_article_2} 
{sample_article_3}

WRITE LIKE A REAL HUMAN JOURNALIST:
- Use normal everyday words, not fancy ones (avoid "stellar", "coveted", "bolster")
- Make some sentences a bit clunky or awkward - humans aren't perfect writers
- Add small grammatical quirks humans make
- Use "but" and "and" to start sentences sometimes  
- Don't explain every single detail - assume readers know football
- Make paragraph breaks feel natural, not perfectly structured
- Use contractions naturally (he's, won't, they're, can't)
- Include repetitive phrases - humans repeat themselves 
- Add minor redundancies in explanations
- Use simple words instead of complex ones
- Make some transitions between topics slightly abrupt 
- Include small errors in flow that humans would make
- Don't polish everything perfectly - leave rough edges
- Sound like you're explaining to a friend who knows football
- Use "reportedly" and "sources say" but don't overdo it
- Mix short choppy sentences with longer ones randomly
- Add casual observations and brief analysis
- Write with slight imperfections in rhythm and pace

Write 450-550 words. Sound completely human, not AI. Make it slightly imperfect."""

        return prompt
    
    def load_enhanced_search_results(self, file_path: str) -> Optional[Dict]:
        """Load enhanced search results from JSON file"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ Loaded research data from: {file_path.name}")
            print(f"   📊 Sources: {data.get('total_sources_processed', 0)}")
            print(f"   📝 Total words: {data.get('total_words_collected', 0)}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error loading research data: {e}")
            return None
    
    def save_generated_article(self, article_data: Dict, original_headline: str) -> str:
        """Save generated article to final_article folder"""
        try:
            # Create timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Clean headline for filename
            clean_headline = "".join(c for c in original_headline if c.isalnum() or c in (' ', '-', '_')).rstrip()
            clean_headline = clean_headline.replace(' ', '_')[:50]
            
            # Create filenames
            txt_filename = f"gemini_article_{clean_headline}_{timestamp}.txt"
            json_filename = f"gemini_article_{clean_headline}_{timestamp}.json"
            
            txt_filepath = self.final_article_dir / txt_filename
            json_filepath = self.final_article_dir / json_filename
            
            # Save text file (human-readable article)
            with open(txt_filepath, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("GEMINI-GENERATED HUMAN-STYLE SPORTS ARTICLE\n")
                f.write("="*80 + "\n\n")
                
                # Article metadata
                f.write("ARTICLE INFORMATION:\n")
                f.write("-"*40 + "\n")
                f.write(f"Original Headline: {article_data.get('headline', 'Unknown')}\n")
                f.write(f"Generated: {article_data.get('timestamp', 'Unknown')}\n")
                f.write(f"Model: {article_data.get('model_used', 'Unknown')}\n")
                f.write(f"Word Count: {article_data.get('word_count', 0)}\n")
                f.write(f"Sources Analyzed: {article_data.get('sources_analyzed', 0)}\n")
                f.write(f"Generation Time: {article_data.get('generation_time', 0)}s\n\n")
                
                # Main article content
                f.write("GENERATED ARTICLE:\n")
                f.write("="*80 + "\n\n")
                f.write(article_data.get('article_text', ''))
                f.write("\n\n" + "="*80 + "\n")
                f.write("END OF ARTICLE\n")
                f.write("="*80 + "\n")
            
            # Save JSON file (full data)
            with open(json_filepath, 'w', encoding='utf-8') as json_f:
                json.dump(article_data, json_f, indent=2, ensure_ascii=False)
            
            print(f"💾 Generated article saved to:")
            print(f"   📄 Article: {txt_filepath}")
            print(f"   📄 Data: {json_filepath}")
            
            return str(txt_filepath)
            
        except Exception as e:
            print(f"❌ Error saving article: {e}")
            return ""
    
    def interactive_article_generation(self):
        """Interactive session for generating articles from enhanced search results"""
        print("🤖 Gemini Article Generation Tester")
        print("="*70)
        
        if not self.available:
            print("❌ Gemini AI not configured.")
            print("   Required: GEMINI_API_KEY environment variable")
            return
        
        print("✅ Ready to generate human-style articles from enhanced search results")
        
        while True:
            print(f"\n📂 Available enhanced search files:")
            
            # List available JSON files in testing_output
            json_files = list(self.testing_output_dir.glob("enhanced_search_research_*.json"))
            
            if not json_files:
                print("   ❌ No enhanced search result files found in testing_output/")
                print("   Please run test_enhanced_search_content.py first to generate research data.")
                break
            
            for i, file_path in enumerate(json_files, 1):
                print(f"   {i}. {file_path.name}")
            
            print(f"\n📝 Select a file to generate article from (1-{len(json_files)}):")
            try:
                choice = input("File number: ").strip()
                if not choice.isdigit() or not (1 <= int(choice) <= len(json_files)):
                    print("❌ Invalid selection.")
                    continue
                
                selected_file = json_files[int(choice) - 1]
                
                # Load research data
                research_data = self.load_enhanced_search_results(selected_file)
                
                if not research_data:
                    print("❌ Failed to load research data.")
                    continue
                
                # Generate article
                article_result = self.generate_human_article_from_sources(research_data)
                
                if article_result.get('status') == 'success':
                    # Show preview
                    article_text = article_result.get('article_text', '')
                    preview = article_text[:500] + "..." if len(article_text) > 500 else article_text
                    
                    print(f"\n📖 Generated Article Preview:")
                    print("-" * 50)
                    print(preview)
                    print("-" * 50)
                    
                    # Save article
                    saved_path = self.save_generated_article(
                        article_result, 
                        research_data.get('headline', 'Unknown')
                    )
                    
                    print(f"\n📊 Generation Summary:")
                    print(f"   ✅ Status: Success")
                    print(f"   📝 Article Length: {article_result.get('word_count', 0)} words")
                    print(f"   📊 Sources Used: {article_result.get('sources_analyzed', 0)}")
                    print(f"   ⏱️  Generation Time: {article_result.get('generation_time', 0)}s")
                else:
                    error = article_result.get('error', 'Unknown error')
                    print(f"\n❌ Article Generation Failed:")
                    print(f"   Error: {error}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Session interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
            
            print(f"\n" + "="*70)
            continue_test = input("Generate another article? (y/n): ").strip().lower()
            if continue_test not in ['y', 'yes']:
                break
        
        print("\n👋 Article generation session ended. Check the final_article folder for results.")
    
    def test_latest_enhanced_search(self):
        """Quick test using the most recent enhanced search result"""
        print("🚀 Quick Test: Generate article from latest enhanced search result")
        print("="*70)
        
        # Find the most recent enhanced search file
        json_files = list(self.testing_output_dir.glob("enhanced_search_research_*.json"))
        
        if not json_files:
            print("❌ No enhanced search result files found.")
            print("   Please run test_enhanced_search_content.py first.")
            return
        
        # Get the most recent file
        latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
        
        print(f"📂 Using latest file: {latest_file.name}")
        
        # Load and process
        research_data = self.load_enhanced_search_results(latest_file)
        
        if research_data:
            article_result = self.generate_human_article_from_sources(research_data)
            
            if article_result.get('status') == 'success':
                saved_path = self.save_generated_article(
                    article_result, 
                    research_data.get('headline', 'Unknown')
                )
                
                print(f"\n🎯 Quick Test Complete!")
                print(f"   📝 Generated: {article_result.get('word_count', 0)} words")
                print(f"   📊 From: {article_result.get('sources_analyzed', 0)} sources")
                print(f"   💾 Saved to: final_article/")
            else:
                print(f"❌ Generation failed: {article_result.get('error', 'Unknown')}")


def main():
    """Main function"""
    tester = GeminiArticleTester()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        tester.test_latest_enhanced_search()
    else:
        tester.interactive_article_generation()


if __name__ == "__main__":
    main()