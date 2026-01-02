"""
Sports Article Generator using Gemini AI
Generates SEO-optimized sports articles from research collected by Perplexity AI
Specifically designed for sports content (football, cricket, basketball, etc.)
"""

import os
import json
import logging
import sys
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Ensure console can handle UTF-8 output
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Load environment variables
load_dotenv()

# Setup logging
root_logger = logging.getLogger()
if not root_logger.handlers:
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler('sports_article_generator.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.INFO)


class SportsArticleGenerator:
    """
    Generate SEO-optimized sports articles from Perplexity research using Gemini AI
    Takes research context and creates human-like, engaging sports articles
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Sports Article Generator
        
        Args:
            api_key (str): Google Gemini API key (defaults to GOOGLE_API_KEY env variable)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        
        if not self.api_key:
            logging.warning("⚠️  GOOGLE_API_KEY not found in environment variables")
            self.model = None
            return
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Generation configuration optimized for sports articles
        self.generation_config = {
            'temperature': 0.9,          # Balanced creativity for engaging writing
            'top_p': 0.95,
            'top_k': 50,
            'max_output_tokens': 8000,  # Comprehensive sports articles
            'candidate_count': 1,
        }
    
    @property
    def available(self) -> bool:
        """Check if the generator is available (has valid API key and model)"""
        return self.model is not None
    
    def generate_article_from_research(self, research_context: Dict) -> Dict:
        """
        Generate a sports article from Perplexity research data
        
        Args:
            research_context (Dict): Contains:
                - article_headline: Original headline
                - article_source: Original source
                - article_category: Sports category (cricket, football, basketball)
                - article_url: Original article URL
                - published_date: Publication date
                - importance_score: Importance ranking
                - research_data: Full research from Perplexity AI
                    - content: Research text
                    - citations: Source citations
                    - sources: List of sources
        
        Returns:
            Dict: Generated article with:
                - status: 'success' or 'error'
                - headline: Article headline
                - article_content: Full HTML article
                - word_count: Number of words
                - section_count: Number of sections
                - seo_metadata: SEO details
                - sources: Source citations
        """
        try:
            if not self.model:
                logging.error("❌ Gemini model not initialized - API key missing")
                return {
                    'status': 'error',
                    'error': 'Gemini API key not configured',
                    'headline': research_context.get('article_headline', '')
                }
            
            headline = research_context.get('article_headline', '')
            source = research_context.get('article_source', '')
            category = research_context.get('article_category', '')
            url = research_context.get('article_url', '')
            importance_score = research_context.get('importance_score', 0)
            research_data = research_context.get('research_data', {})
            
            # Extract research content
            research_content = research_data.get('research_sections', {}).get('comprehensive', {}).get('content', '')
            if not research_content:
                research_content = research_data.get('content', '')
            
            sources = research_data.get('compiled_sources', [])
            citations = research_data.get('compiled_citations', [])
            
            logging.info(f"\n{'='*70}")
            logging.info(f"🎯 GEMINI SPORTS ARTICLE GENERATION")
            logging.info(f"{'='*70}")
            logging.info(f"📰 Headline: {headline[:70]}")
            logging.info(f"📍 Source: {source}")
            logging.info(f"🏷️  Category: {category}")
            logging.info(f"📊 Importance Score: {importance_score}")
            logging.info(f"📚 Research Length: {len(research_content)} characters")
            logging.info(f"🔗 Sources Available: {len(sources)}")
            
            # Check if this is combined research from multiple sources
            research_method = research_data.get('research_method', 'standard')
            if research_method == 'hybrid_perplexity_enhanced_search':
                sources_used = research_data.get('sources_used', [])
                logging.info(f"🔄 Using HYBRID RESEARCH from: {', '.join(sources_used)}")
                statistics = research_data.get('statistics', {})
                if statistics:
                    logging.info(f"   📊 Research Statistics:")
                    logging.info(f"      🌐 Perplexity: {'✅' if statistics.get('perplexity_available') else '❌'}")
                    logging.info(f"      🔍 Enhanced Search: {'✅' if statistics.get('enhanced_search_available') else '❌'}")
                    logging.info(f"      📚 Total Sources: {statistics.get('total_sources', 0)}")
            else:
                logging.info(f"🔄 Using standard research method: {research_method}")
            
            # Build comprehensive prompt for sports article generation
            prompt = self._build_sports_article_prompt(
                headline=headline,
                source=source,
                category=category,
                importance_score=importance_score,
                research_content=research_content,
                sources=sources,
                citations=citations
            )
            
            logging.info(f"\n🔄 Sending to Gemini for article generation...")
            
            # Generate article using Gemini
            response = self.model.generate_content(prompt, generation_config=self.generation_config)
            
            if not response or not response.text:
                logging.error("❌ Gemini returned empty response")
                return {
                    'status': 'error',
                    'error': 'Empty response from Gemini',
                    'headline': headline
                }
            
            article_html = response.text
            
            logging.info(f"✅ Article generated successfully!")
            logging.info(f"   📄 Article length: {len(article_html)} characters")
            
            # Post-process and extract metadata
            article_html = self._post_process_article(article_html)
            
            # Extract the new headline from Gemini's generated content
            extracted_headline = self._extract_headline_from_content(article_html)
            final_headline = extracted_headline if extracted_headline else headline
            
            logging.info(f"📝 Original headline: {headline}")
            logging.info(f"🎯 Generated headline: {final_headline}")
            
            metadata = self._extract_metadata(article_html, final_headline, category)
            
            # Build complete article response
            article_response = {
                'status': 'success',
                'headline': final_headline,  # Use the generated headline
                'original_headline': headline,  # Keep original for reference
                'article_content': article_html,
                'category': category,
                'source': source,
                'url': url,
                'importance_score': importance_score,
                'generated_at': datetime.now().isoformat(),
                'word_count': metadata.get('word_count', 0),
                'section_count': metadata.get('section_count', 0),
                'seo_metadata': {
                    'title': metadata.get('title', final_headline),
                    'slug': metadata.get('slug', ''),
                    'meta_description': metadata.get('meta_description', ''),
                    'keywords': metadata.get('keywords', [])
                },
                'sources': sources,
                'citations': citations,
                'research_summary': {
                    'total_sources': len(sources),
                    'research_length': len(research_content),
                    'category': category
                }
            }
            
            logging.info(f"\n{'='*70}")
            logging.info(f"✅ ARTICLE GENERATION COMPLETE")
            logging.info(f"{'='*70}")
            logging.info(f"📊 Word Count: {metadata.get('word_count', 0):,}")
            logging.info(f"📑 Sections: {metadata.get('section_count', 0)}")
            logging.info(f"🔗 Sources Used: {len(sources)}")
            logging.info(f"{'='*70}\n")
            
            return article_response
            
        except Exception as e:
            logging.error(f"❌ Error generating article: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'headline': research_context.get('article_headline', '')
            }
    
    def _build_sports_article_prompt(self, 
                                     headline: str,
                                     source: str,
                                     category: str,
                                     importance_score: float,
                                     research_content: str,
                                     sources: list,
                                     citations: list) -> str:
        """
        Build comprehensive prompt for sports article generation
        
        Args:
            headline: Original article headline
            source: Original source
            category: Sports category
            importance_score: Article importance
            research_content: Full research from Perplexity
            sources: List of research sources
            citations: Source citations
            
        Returns:
            str: Complete prompt for Gemini
        """
        
        # Prepare sources text from the sources list
        sources_text = "\n".join([f"{s}" for s in sources[:5]])  # Top 5 sources
        
        # Build comprehensive research content with source attribution
        if "RESEARCH FROM PERPLEXITY AI:" in research_content and "RESEARCH FROM ENHANCED SEARCH" in research_content:
            research_attribution = "This article combines comprehensive research from multiple sources including Perplexity AI and Enhanced Search with full article content for maximum accuracy and depth."
        elif "RESEARCH FROM ENHANCED SEARCH" in research_content:
            research_attribution = "This article uses Enhanced Search research with full article content from trusted sources."
        else:
            research_attribution = "This article uses comprehensive research from trusted internet sources."
        
        comprehensive_research = f"{research_content}"
        
        # Focus keyword hint based on headline
        focus_keyword_hint = headline.split()[0] if headline else "sports"
        
        prompt = f"""Write a sports news article using this research: {comprehensive_research}

RESEARCH QUALITY: {research_attribution}


Research content: {comprehensive_research}

ORIGINAL HEADLINE: {headline}
CATEGORY: {category}
FOCUS KEYWORD: {focus_keyword_hint}

SOURCE LINKS (MUST use 3-4 naturally embedded):
{sources_text}

Style samples (learn writing patterns only, don't copy content):
{{With the January transfer window approaching, Sheffield United's on-loan Nottingham Forest defender Tyler Bindon is facing an uncertain future at Bramall Lane.

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

"Let's see what happens [regarding his future]. He's playing and I'm not going to give everything away to Wrexham, but I don't think there's going to be a huge amount of changes to the back four because of the way they've played.}}
{{

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

Whether that form would translate into hitting goals for Stoke is another question, though. Regardless, Stoke should launch an ambitious move for Piroe this winter as they look to force their way into the play-off picture once more.}}
{{Chelsea join race for Antoine Semenyo! Blues make contact with Bournemouth star's camp over potential £65m January transfer
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

Bournemouth are due to finish off 2025 with Premier League games against Brentford and Chelsea before the transfer window opens on January 1.  The games could potentially be Semenyo's last in a Bournemouth shirt if he does indeed make a quick decision on his future.}}

WRITE LIKE A REAL HUMAN SPORTS JOURNALIST (NOT AI):
- Keep sentences SHORT and simple - max 15-20 words per sentence
- Use simple, normal words that people actually say (avoid "stellar", "coveted", "bolster", "remarkable", "extraordinary", "monumental", "unprecedented")
- Make sentences direct and to the point - no long explanations
- Cut out unnecessary words - be concise
- One idea per sentence - don't combine multiple thoughts
- Make sentences a bit messy and imperfect - humans don't write perfectly
- Add small grammar mistakes that real people make
- Start sentences with "And" and "But" sometimes like people talk
- Don't explain everything - assume readers know the sport
- Make paragraph breaks feel random, not perfectly organized  
- Use contractions like people talk (he's, won't, they're, can't, doesn't)
- Repeat yourself sometimes - humans do this naturally
- Use really simple words instead of fancy ones
- Jump between topics without perfect transitions
- Include small flow problems that humans make when writing
- Don't make everything perfect - leave it rough around the edges
- Write like you're telling a friend who follows sports
- Use "apparently" and "sources say" but don't overuse it
- Mix super short sentences (5-8 words) with medium ones (10-15 words)
- Add your own quick thoughts and observations
- Make the rhythm feel choppy and natural, not smooth
- Use filler words and phrases humans use
- Don't sound like a textbook or formal report
- Sound conversational and slightly informal
- Make some word choices that aren't quite right but humans would use
- Add redundant information that humans typically include
- Use "pretty", "really", "quite", "seems like" to sound casual
- Break up long thoughts into multiple short sentences

WORDPRESS-READY FORMATTING RULES:

HEADLINE CREATION PROCESS:
After you write the complete article, create an ATTRACTIVE headline that will grab readers' attention. Your headline should:
- Be 50-70 characters long (optimal for SEO and social sharing)
- Include the main player/team name and the key action/event
- Use powerful action words that create urgency or excitement
- Include specific numbers, scores, or timeframes when available
- Make it click-worthy while staying truthful to the story
- Create curiosity without being clickbait: hint at surprising details
- Use present tense for recent events, past tense for completed actions
- Include team rivalries or high-stakes context when relevant
- Make it shareable on social media platforms
- don't use these special symbols (!, ?, :, ;, ", ', - etc.)
- Use ONE <h1> tag only

HEADLINE EXAMPLES FOR INSPIRATION:
- "Messi Breaks Silence on PSG Exit After Heated Dressing Room Confrontation"
- "Liverpool Star Confirms January Exit Following Contract Dispute"  
- "United Target Rejects 80 Million Bid in Shocking Transfer Twist"
- "City Boss Reveals Haaland Injury Truth After Mystery Absence"
- "Arsenal Legend Slams Current Squad After Embarrassing Defeat"
- "Chelsea Confirm New Signing Hours Before Transfer Deadline"
- "Ronaldo Drops Retirement Bombshell in Emotional Interview"

HTML STRUCTURE (WordPress Ready):
- Use <p> tags for ALL paragraphs
- Use <h2> tags for main sections (3-4 sections)
- Use <h3> tags for subsections if needed
- Use <strong> tags for bold text (never **text**)
- Use <blockquote> tags for quotes
- Use <table> tags with proper structure if data tables needed
- Use <ul>/<ol> and <li> tags for lists if needed

EXTERNAL LINKING (MANDATORY):
- Embed 3-4 source links naturally in sentences
- Format: <a href="URL" target="_blank" rel="noopener noreferrer">Source Name</a>
- Examples: "<a href="URL" target="_blank" rel="noopener noreferrer">ESPN reported</a> the signing"
- "According to <a href="URL" target="_blank" rel="noopener noreferrer">BBC Sport</a>..."

SEO OPTIMIZATION:
- Use focus keyword in first paragraph
- Include related keywords naturally throughout
- Write meta-description worthy opening paragraph
- Use semantic HTML structure
- Include entity names (player names, team names, locations)

CONTENT STRUCTURE:
- Opening: State what happened (2-3 sentences with focus keyword)
- Headline should match the opening paragraph's main story
- 3-4 H2 sections covering different aspects of the story
- Include quotes if available from research (use proper attribution)
- Build narrative tension and reader engagement throughout
- End with next fixture/event, transfer implications, or current status
- Ensure headline promises are delivered in the article content
- 600-800 words total

HEADLINE-CONTENT ALIGNMENT:
- If headline mentions "breaks silence" → include quotes or statements
- If headline mentions "confirms/denies" → provide the confirmation details  
- If headline mentions numbers/stats → include specific data in article
- If headline mentions "shocking/stunning" → explain why it's surprising
- If headline mentions timeframes → clarify when events happened/will happen

Write 600-800 words. Sound completely human, not AI. Make it slightly imperfect but WordPress-ready with proper HTML structure.

DO WRITE LIKE THIS:
- State facts clearly and directly
- Provide relevant background and context
- Use specific details that show expertise
- Write with natural authority on the subject
- Let the story tell itself without over-commentary
- Use industry knowledge to add depth
- Write for readers who follow the sport seriously"""
        
        return prompt
    
    def _post_process_article(self, article_html: str) -> str:
        """
        Post-process the generated article to ensure quality
        
        Args:
            article_html (str): Raw HTML from Gemini
            
        Returns:
            str: Cleaned article HTML
        """
        # Remove any markdown artifacts if present
        article_html = article_html.replace('**', '')
        article_html = article_html.replace('##', '<h2>')
        article_html = article_html.replace('###', '<h3>')
        
        # Ensure proper paragraph wrapping if needed
        lines = article_html.split('\n')
        processed_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('<') and not any(tag in stripped for tag in ['<h2>', '<h3>', '<h4>', '<table>']):
                if not stripped.startswith('<'):
                    if '<p>' not in stripped and '<li>' not in stripped:
                        processed_lines.append(f"<p>{stripped}</p>")
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            elif stripped:
                processed_lines.append(line)
        
        article_html = '\n'.join(processed_lines)
        
        return article_html
    
    def _extract_headline_from_content(self, article_html: str) -> Optional[str]:
        """
        Extract the new headline from Gemini's generated content
        
        Args:
            article_html (str): Generated article HTML
            
        Returns:
            str: Extracted headline or None if not found
        """
        import re
        
        # Try to find <h1> tag first
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            headline = h1_match.group(1).strip()
            # Clean up any HTML tags inside
            headline = re.sub(r'<[^>]+>', '', headline)
            logging.info(f"🎯 Extracted headline from <h1> tag: {headline}")
            return headline
        
        # Try to find markdown # heading at the start of lines
        lines = article_html.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# ') and not line.startswith('##'):
                headline = line.replace('# ', '').strip()
                logging.info(f"🎯 Extracted headline from markdown: {headline}")
                return headline
        
        # Try to find the first strong/bold text that looks like a headline
        strong_match = re.search(r'<strong[^>]*>(.*?)</strong>', article_html, re.IGNORECASE | re.DOTALL)
        if strong_match:
            potential_headline = strong_match.group(1).strip()
            # Clean up HTML tags
            potential_headline = re.sub(r'<[^>]+>', '', potential_headline)
            # Check if it looks like a headline (reasonable length, not too long)
            if 20 <= len(potential_headline) <= 100:
                logging.info(f"🎯 Extracted headline from <strong> tag: {potential_headline}")
                return potential_headline
        
        logging.warning("⚠️ Could not extract new headline from generated content")
        return None

    def _generate_seo_slug(self, headline: str) -> str:
        """
        Generate SEO-optimized slug from headline (max 75 characters)
        
        Args:
            headline (str): Article headline
            
        Returns:
            str: SEO-optimized slug
        """
        import re
        
        # Convert to lowercase and remove special characters
        slug = re.sub(r'[^\w\s]', '', headline.lower()).strip()
        
        # Replace spaces with hyphens
        slug = re.sub(r'[\s]+', '-', slug).strip('-')
        
        # Advanced stop words removal for sports content
        stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                     'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 
                     'should', 'may', 'might', 'must', 'can', 'his', 'her', 'its', 'their',
                     'this', 'that', 'these', 'those', 'who', 'what', 'when', 'where', 
                     'why', 'how', 'which', 'much', 'many', 'more', 'most', 'some', 'any',
                     'into', 'onto', 'upon', 'over', 'under', 'above', 'below', 'between',
                     'through', 'during', 'before', 'after', 'while', 'since', 'until']
        
        # Split slug into parts
        parts = slug.split('-')
        
        # Keep important sports-related words even if they seem like stop words
        sports_keywords = ['goal', 'win', 'loss', 'game', 'match', 'team', 'player', 'coach',
                          'season', 'league', 'cup', 'final', 'semi', 'quarter', 'round',
                          'transfer', 'sign', 'deal', 'contract', 'injury', 'return',
                          'record', 'best', 'worst', 'first', 'last', 'new', 'old']
        
        # Remove stop words only if slug is too long, but preserve sports keywords and numbers
        if len(slug) > 60:  # Start removing stop words earlier to avoid truncation
            filtered_parts = []
            for part in parts:
                # Keep if: not a stop word, is a sports keyword, contains numbers, or is long (likely important)
                if (part not in stop_words or 
                    part in sports_keywords or 
                    any(char.isdigit() for char in part) or 
                    len(part) > 5):
                    filtered_parts.append(part)
            
            if filtered_parts:  # Ensure we don't create empty slug
                slug = '-'.join(filtered_parts)
        
        # If still too long, prioritize first few words (usually most important)
        if len(slug) > 75:
            parts = slug.split('-')
            # Keep first 4-6 words depending on length
            truncated_parts = []
            current_length = 0
            
            for part in parts:
                if current_length + len(part) + 1 <= 75:  # +1 for hyphen
                    truncated_parts.append(part)
                    current_length += len(part) + 1
                else:
                    break
            
            if truncated_parts:
                slug = '-'.join(truncated_parts)
            else:
                # Fallback: truncate at 75 characters at word boundary
                slug = slug[:75].rsplit('-', 1)[0].strip('-')
        
        # Ensure minimum length and no empty strings
        if len(slug) < 3:
            slug = 'sports-news'
        
        slug = slug.strip('-')
        logging.info(f"🔗 Generated optimized SEO slug: '{slug}' ({len(slug)}/75 chars)")
        
        return slug

    def _extract_metadata(self, article_html: str, headline: str, category: str) -> Dict:
        """
        Extract metadata from generated article
        
        Args:
            article_html (str): Generated article HTML
            headline (str): Original headline
            category (str): Sport category
            
        Returns:
            Dict: Metadata including word count, sections, etc.
        """
        # Count words
        text_content = article_html.replace('<h2>', ' ').replace('<h3>', ' ').replace('<p>', ' ')
        text_content = text_content.replace('</h2>', ' ').replace('</h3>', ' ').replace('</p>', ' ')
        words = len([w for w in text_content.split() if w])
        
        # Count sections (h2 tags)
        section_count = article_html.count('<h2>')
        
        # Extract first paragraph for meta description
        import re
        first_para = re.search(r'<p>(.+?)</p>', article_html)
        meta_description = first_para.group(1)[:160] if first_para else headline[:160]
        
        # Generate SEO-optimized slug (max 75 characters)
        slug = self._generate_seo_slug(headline)
        
        # Generate keywords
        keywords = [
            headline.split()[0] if headline.split() else category,
            category,
            'sports',
            'sports news',
            'analysis'
        ]
        
        return {
            'word_count': words,
            'section_count': section_count,
            'title': headline,
            'slug': slug,
            'meta_description': meta_description,
            'keywords': keywords
        }
