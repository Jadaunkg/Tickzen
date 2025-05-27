import {
  ArrowRight,
  BarChart3,
  Zap,
  Shield,
  Clock,
  TrendingUp,
  Globe,
  CheckCircle,
  X,
  LineChart,
  PieChart,
  Layers,
  FileText,
  Newspaper,
  Users,
  Star,
  Award,
  Lock,
  Sparkles,
  Building2,
  BarChartIcon as ChartBar,
  Bot,
  Gauge,
  DollarSign,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import Link from "next/link"
import { Chart } from "@/components/ui/chart"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-green-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <BarChart3 className="h-8 w-8 text-green-600" />
            <span className="text-xl font-bold text-gray-900">StockAnalyzer Pro</span>
          </div>
          <nav className="hidden md:flex items-center space-x-6">
            <Link href="#features" className="text-gray-600 hover:text-gray-900">
              Features
            </Link>
            <Link href="#comparison" className="text-gray-600 hover:text-gray-900">
              Compare
            </Link>
            <Link href="#pricing" className="text-gray-600 hover:text-gray-900">
              Pricing
            </Link>
            <Link href="#testimonials" className="text-gray-600 hover:text-gray-900">
              Reviews
            </Link>
          </nav>
          <div className="flex items-center space-x-4">
            <Button variant="ghost">Sign In</Button>
            <Button className="bg-green-600 hover:bg-green-700">Get Started</Button>
          </div>
        </div>
      </header>

      {/* Enhanced Hero Section */}
      <section className="py-20 lg:py-32 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-green-50/50 to-transparent"></div>
        <div className="container mx-auto px-4 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Badge className="bg-green-100 text-green-800 hover:bg-green-100">
                    <Sparkles className="h-3 w-3 mr-1" />
                    AI-Powered Stock Analysis
                  </Badge>
                  <Badge variant="outline" className="border-green-600 text-green-600">
                    <Award className="h-3 w-3 mr-1" />
                    #1 Rated Platform
                  </Badge>
                </div>
                <h1 className="text-4xl lg:text-6xl font-bold text-gray-900 leading-tight">
                  Turn Stock Data Into <span className="text-green-600">Revenue-Generating Content</span>
                </h1>
                <p className="text-xl text-gray-600 leading-relaxed">
                  Generate institutional-grade 3000-word stock analysis reports in minutes. Automatically publish to
                  WordPress with one click. Join 500+ financial professionals saving 20+ hours weekly.
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-4">
                <Button size="lg" className="bg-green-600 hover:bg-green-700">
                  Start Free Trial
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
                <Button size="lg" variant="outline" className="border-green-600 text-green-600 hover:bg-green-50">
                  <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z" />
                  </svg>
                  Watch 2-Min Demo
                </Button>
              </div>
              <div className="grid grid-cols-3 gap-4 pt-4">
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-600">10K+</p>
                  <p className="text-sm text-gray-600">Reports Generated</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-600">500+</p>
                  <p className="text-sm text-gray-600">Active Users</p>
                </div>
                <div className="text-center">
                  <p className="text-3xl font-bold text-green-600">4.9/5</p>
                  <p className="text-sm text-gray-600">User Rating</p>
                </div>
              </div>
            </div>
            <div className="relative">
              {/* Main Dashboard Preview */}
              <div className="bg-white rounded-2xl shadow-2xl p-6 border relative z-10">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <BarChart3 className="h-5 w-5 text-green-600" />
                      <h3 className="font-semibold text-gray-900">AAPL Analysis Dashboard</h3>
                    </div>
                    <Badge className="bg-green-100 text-green-800">Live</Badge>
                  </div>

                  {/* Real-time Chart */}
                  <div className="h-64 w-full">
                    <Chart
                      type="area"
                      options={{
                        chart: {
                          toolbar: {
                            show: false,
                          },
                          animations: {
                            enabled: true,
                            easing: "easeinout",
                            speed: 800,
                            animateGradually: {
                              enabled: true,
                              delay: 150,
                            },
                            dynamicAnimation: {
                              enabled: true,
                              speed: 350,
                            },
                          },
                        },
                        stroke: {
                          curve: "smooth",
                          width: 3,
                        },
                        colors: ["#16a34a", "#fbbf24"],
                        grid: {
                          borderColor: "#f3f4f6",
                          row: {
                            colors: ["transparent", "transparent"],
                            opacity: 0.5,
                          },
                        },
                        xaxis: {
                          categories: [
                            "Jan",
                            "Feb",
                            "Mar",
                            "Apr",
                            "May",
                            "Jun",
                            "Jul",
                            "Aug",
                            "Sep",
                            "Oct",
                            "Nov",
                            "Dec",
                          ],
                          labels: {
                            style: {
                              colors: "#6b7280",
                              fontSize: "10px",
                            },
                          },
                        },
                        yaxis: {
                          labels: {
                            style: {
                              colors: "#6b7280",
                              fontSize: "10px",
                            },
                            formatter: (value) => {
                              return `$${value.toFixed(0)}`
                            },
                          },
                        },
                        legend: {
                          show: true,
                          position: "top",
                          horizontalAlign: "right",
                          fontSize: "12px",
                        },
                        tooltip: {
                          theme: "light",
                          x: {
                            show: false,
                          },
                        },
                        fill: {
                          type: "gradient",
                          gradient: {
                            shade: "light",
                            type: "vertical",
                            shadeIntensity: 0.5,
                            gradientToColors: ["#dcfce7", "#fef3c7"],
                            inverseColors: false,
                            opacityFrom: 0.7,
                            opacityTo: 0.1,
                            stops: [0, 100],
                          },
                        },
                      }}
                      series={[
                        {
                          name: "Stock Price",
                          data: [145, 152, 158, 165, 149, 168, 176, 179, 170, 183, 191, 198],
                        },
                        {
                          name: "S&P 500",
                          data: [140, 145, 148, 152, 147, 155, 160, 162, 158, 165, 170, 175],
                        },
                      ]}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="bg-gradient-to-r from-green-50 to-green-100 p-3 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">AI Score</span>
                        <TrendingUp className="h-4 w-4 text-green-600" />
                      </div>
                      <p className="text-2xl font-bold text-green-600">8.5/10</p>
                      <p className="text-xs text-green-700">Strong Buy Signal</p>
                    </div>
                    <div className="bg-gradient-to-r from-yellow-50 to-yellow-100 p-3 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-600">Risk Level</span>
                        <Shield className="h-4 w-4 text-yellow-600" />
                      </div>
                      <p className="text-2xl font-bold text-yellow-600">Medium</p>
                      <p className="text-xs text-yellow-700">Volatility: 24.3%</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <div className="flex items-center space-x-2">
                      <Avatar className="h-6 w-6">
                        <AvatarImage src="/placeholder.svg?height=24&width=24" />
                        <AvatarFallback>JD</AvatarFallback>
                      </Avatar>
                      <span className="text-xs text-gray-500">Analysis by John Doe</span>
                    </div>
                    <Button size="sm" className="bg-green-600 hover:bg-green-700 text-xs">
                      Publish to WordPress
                    </Button>
                  </div>
                </div>
              </div>

              {/* Floating Elements */}
              <div className="absolute -top-4 -right-4 bg-white p-3 rounded-xl shadow-lg border animate-pulse">
                <div className="flex items-center space-x-2">
                  <Globe className="h-5 w-5 text-green-600" />
                  <span className="text-sm font-medium">3 Sites Connected</span>
                </div>
              </div>

              <div className="absolute -bottom-4 -left-4 bg-white p-3 rounded-xl shadow-lg border">
                <div className="flex items-center space-x-2">
                  <FileText className="h-5 w-5 text-green-600" />
                  <span className="text-sm font-medium">2,847 words generated</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Badges */}
      <section className="py-12 bg-white border-y border-gray-200">
        <div className="container mx-auto px-4">
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12">
            <div className="flex items-center space-x-2 text-gray-600">
              <Lock className="h-5 w-5" />
              <span className="text-sm font-medium">SOC 2 Compliant</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <Shield className="h-5 w-5" />
              <span className="text-sm font-medium">Bank-Level Security</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <Award className="h-5 w-5" />
              <span className="text-sm font-medium">ISO 27001 Certified</span>
            </div>
            <div className="flex items-center space-x-2 text-gray-600">
              <Building2 className="h-5 w-5" />
              <span className="text-sm font-medium">Enterprise Ready</span>
            </div>
          </div>
        </div>
      </section>

      {/* Integration Logos */}
      <section className="py-16 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center mb-8">
            <h3 className="text-lg font-semibold text-gray-900">Trusted by Leading Financial Platforms</h3>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-16 opacity-60">
            <div className="text-2xl font-bold text-gray-400">Bloomberg</div>
            <div className="text-2xl font-bold text-gray-400">Reuters</div>
            <div className="text-2xl font-bold text-gray-400">Yahoo Finance</div>
            <div className="text-2xl font-bold text-gray-400">MarketWatch</div>
            <div className="text-2xl font-bold text-gray-400">WordPress</div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section id="testimonials" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4 mb-16">
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Success Stories</Badge>
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">Loved by Financial Professionals</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              See how StockAnalyzer Pro is transforming the way financial content is created
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card className="border-2 hover:border-green-200 transition-colors">
              <CardHeader>
                <div className="flex items-center space-x-4 mb-4">
                  <Avatar className="h-12 w-12">
                    <AvatarImage src="/placeholder.svg?height=48&width=48" alt="Sarah Chen" />
                    <AvatarFallback>SC</AvatarFallback>
                  </Avatar>
                  <div>
                    <h4 className="font-semibold text-gray-900">Sarah Chen</h4>
                    <p className="text-sm text-gray-600">Financial Analyst, Morgan Stanley</p>
                  </div>
                </div>
                <div className="flex text-yellow-400">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-current" />
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">
                  "StockAnalyzer Pro has revolutionized my workflow. What used to take me 4-5 hours now takes 15
                  minutes. The AI-generated reports are incredibly detailed and accurate. My clients love the
                  comprehensive analysis."
                </p>
                <div className="mt-4 p-3 bg-green-50 rounded-lg">
                  <p className="text-sm text-green-800">
                    <span className="font-semibold">Result:</span> 80% time saved, 3x more reports delivered
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-2 hover:border-green-200 transition-colors">
              <CardHeader>
                <div className="flex items-center space-x-4 mb-4">
                  <Avatar className="h-12 w-12">
                    <AvatarImage src="/placeholder.svg?height=48&width=48" alt="Michael Rodriguez" />
                    <AvatarFallback>MR</AvatarFallback>
                  </Avatar>
                  <div>
                    <h4 className="font-semibold text-gray-900">Michael Rodriguez</h4>
                    <p className="text-sm text-gray-600">Investment Blogger, FinanceDaily.com</p>
                  </div>
                </div>
                <div className="flex text-yellow-400">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-current" />
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">
                  "The WordPress automation feature is a game-changer. I manage 5 finance blogs and StockAnalyzer Pro
                  helps me publish quality content daily. The SEO optimization is fantastic - my traffic has increased
                  by 150%."
                </p>
                <div className="mt-4 p-3 bg-green-50 rounded-lg">
                  <p className="text-sm text-green-800">
                    <span className="font-semibold">Result:</span> 150% traffic increase, 5x content output
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card className="border-2 hover:border-green-200 transition-colors">
              <CardHeader>
                <div className="flex items-center space-x-4 mb-4">
                  <Avatar className="h-12 w-12">
                    <AvatarImage src="/placeholder.svg?height=48&width=48" alt="Emma Thompson" />
                    <AvatarFallback>ET</AvatarFallback>
                  </Avatar>
                  <div>
                    <h4 className="font-semibold text-gray-900">Emma Thompson</h4>
                    <p className="text-sm text-gray-600">Portfolio Manager, Vanguard</p>
                  </div>
                </div>
                <div className="flex text-yellow-400">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-current" />
                  ))}
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600">
                  "The depth of analysis is impressive. It covers everything from technical indicators to macroeconomic
                  factors. My team uses it for initial research, saving us countless hours. The risk assessment is
                  particularly valuable."
                </p>
                <div className="mt-4 p-3 bg-green-50 rounded-lg">
                  <p className="text-sm text-green-800">
                    <span className="font-semibold">Result:</span> 20+ hours saved weekly, Better investment decisions
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Comparison Section */}
      <section id="comparison" className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4 mb-16">
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Platform Comparison</Badge>
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">Why StockAnalyzer Pro Wins</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              See how we compare to other stock analysis platforms in the market
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full bg-white rounded-xl shadow-sm border border-gray-200">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left p-6 font-semibold text-gray-900">Features</th>
                  <th className="text-center p-6">
                    <div className="flex flex-col items-center space-y-2">
                      <div className="bg-green-600 text-white px-3 py-1 rounded-full text-sm">Recommended</div>
                      <span className="font-semibold text-gray-900">StockAnalyzer Pro</span>
                    </div>
                  </th>
                  <th className="text-center p-6 font-semibold text-gray-600">Seeking Alpha</th>
                  <th className="text-center p-6 font-semibold text-gray-600">TradingView</th>
                  <th className="text-center p-6 font-semibold text-gray-600">Manual Analysis</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-100">
                  <td className="p-6 font-medium text-gray-900">AI-Generated Reports</td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <td className="p-6 font-medium text-gray-900">WordPress Integration</td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="p-6 font-medium text-gray-900">Report Length</td>
                  <td className="text-center p-6 text-green-600 font-semibold">2500-3000 words</td>
                  <td className="text-center p-6 text-gray-600">500-1000 words</td>
                  <td className="text-center p-6 text-gray-600">Charts only</td>
                  <td className="text-center p-6 text-gray-600">Varies</td>
                </tr>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <td className="p-6 font-medium text-gray-900">Time to Generate</td>
                  <td className="text-center p-6 text-green-600 font-semibold">2-3 minutes</td>
                  <td className="text-center p-6 text-gray-600">N/A</td>
                  <td className="text-center p-6 text-gray-600">N/A</td>
                  <td className="text-center p-6 text-gray-600">4-6 hours</td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="p-6 font-medium text-gray-900">Technical Analysis</td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <td className="p-6 font-medium text-gray-900">Fundamental Analysis</td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <div className="text-yellow-600 mx-auto">Limited</div>
                  </td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="p-6 font-medium text-gray-900">Risk Assessment</td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <div className="text-yellow-600 mx-auto">Basic</div>
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <div className="text-yellow-600 mx-auto">Manual</div>
                  </td>
                </tr>
                <tr className="border-b border-gray-100 bg-gray-50">
                  <td className="p-6 font-medium text-gray-900">Price Forecasting</td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <div className="text-yellow-600 mx-auto">User-generated</div>
                  </td>
                  <td className="text-center p-6">
                    <div className="text-yellow-600 mx-auto">Manual</div>
                  </td>
                </tr>
                <tr className="border-b border-gray-100">
                  <td className="p-6 font-medium text-gray-900">Multi-site Publishing</td>
                  <td className="text-center p-6">
                    <CheckCircle className="h-6 w-6 text-green-600 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                  <td className="text-center p-6">
                    <X className="h-6 w-6 text-gray-300 mx-auto" />
                  </td>
                </tr>
                <tr>
                  <td className="p-6 font-medium text-gray-900">Starting Price</td>
                  <td className="text-center p-6">
                    <div className="text-green-600 font-bold text-xl">$49/mo</div>
                  </td>
                  <td className="text-center p-6 text-gray-600">$29.99/mo</td>
                  <td className="text-center p-6 text-gray-600">$14.95/mo</td>
                  <td className="text-center p-6 text-gray-600">Free (Time cost)</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="mt-8 text-center">
            <Button size="lg" className="bg-green-600 hover:bg-green-700">
              Start Your Free Trial
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </div>
        </div>
      </section>

      {/* Visual Features Section */}
      <section className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4 mb-16">
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Platform Features</Badge>
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">See StockAnalyzer Pro in Action</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Powerful features designed for financial professionals and content creators
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-12">
            {/* Stock Analysis Visual */}
            <div className="space-y-6">
              <div className="bg-gradient-to-br from-green-50 to-green-100 p-8 rounded-2xl">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">AI-Powered Stock Analysis</h3>
                <div className="bg-white rounded-xl p-6 shadow-sm">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-gray-700">Technical Indicators</span>
                      <Badge className="bg-green-100 text-green-800">20+ Indicators</Badge>
                    </div>
                    <div className="grid grid-cols-4 gap-3">
                      <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">RSI</p>
                        <p className="text-lg font-bold text-green-600">68.5</p>
                      </div>
                      <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">MACD</p>
                        <p className="text-lg font-bold text-green-600">+2.34</p>
                      </div>
                      <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">SMA 50</p>
                        <p className="text-lg font-bold text-gray-900">$165.20</p>
                      </div>
                      <div className="text-center p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-500">Volume</p>
                        <p className="text-lg font-bold text-gray-900">52.3M</p>
                      </div>
                    </div>
                    <div className="pt-4 space-y-3">
                      <div className="flex items-center space-x-3">
                        <Bot className="h-5 w-5 text-green-600" />
                        <span className="text-sm text-gray-600">AI analyzes patterns across 10 years of data</span>
                      </div>
                      <div className="flex items-center space-x-3">
                        <Gauge className="h-5 w-5 text-green-600" />
                        <span className="text-sm text-gray-600">Real-time sentiment analysis from news sources</span>
                      </div>
                      <div className="flex items-center space-x-3">
                        <ChartBar className="h-5 w-5 text-green-600" />
                        <span className="text-sm text-gray-600">Comprehensive fundamental metrics evaluation</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* WordPress Integration Visual */}
            <div className="space-y-6">
              <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-8 rounded-2xl">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">WordPress Auto-Publishing</h3>
                <div className="bg-white rounded-xl p-6 shadow-sm">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between mb-4">
                      <span className="font-medium text-gray-700">Connected Sites</span>
                      <Badge className="bg-blue-100 text-blue-800">3 Active</Badge>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <Globe className="h-5 w-5 text-blue-600" />
                          <div>
                            <p className="font-medium text-sm">InvestmentDaily.com</p>
                            <p className="text-xs text-gray-500">Last published: 2 hours ago</p>
                          </div>
                        </div>
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      </div>
                      <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <Globe className="h-5 w-5 text-blue-600" />
                          <div>
                            <p className="font-medium text-sm">StockAnalysisPro.net</p>
                            <p className="text-xs text-gray-500">Last published: 5 hours ago</p>
                          </div>
                        </div>
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      </div>
                      <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-3">
                          <Globe className="h-5 w-5 text-blue-600" />
                          <div>
                            <p className="font-medium text-sm">MarketInsights.blog</p>
                            <p className="text-xs text-gray-500">Scheduled: Tomorrow 9 AM</p>
                          </div>
                        </div>
                        <Clock className="h-5 w-5 text-yellow-600" />
                      </div>
                    </div>
                    <Button className="w-full bg-blue-600 hover:bg-blue-700">
                      <Newspaper className="h-4 w-4 mr-2" />
                      Publish to All Sites
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ROI Calculator */}
      <section className="py-20 bg-gradient-to-br from-green-600 to-green-700 text-white">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center space-y-4 mb-12">
              <Badge className="bg-white/20 text-white hover:bg-white/20">ROI Calculator</Badge>
              <h2 className="text-3xl lg:text-4xl font-bold">Calculate Your Time & Money Savings</h2>
              <p className="text-xl text-green-100">See how much you could save with StockAnalyzer Pro</p>
            </div>

            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
              <div className="grid md:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <h3 className="text-xl font-semibold">Without StockAnalyzer Pro</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-green-100">Time per analysis:</span>
                      <span className="font-semibold">4-6 hours</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-100">Analyses per week:</span>
                      <span className="font-semibold">2-3</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-100">Weekly time spent:</span>
                      <span className="font-semibold">12-18 hours</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-100">Cost (@ $50/hour):</span>
                      <span className="font-semibold text-xl">$600-900/week</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h3 className="text-xl font-semibold">With StockAnalyzer Pro</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-green-100">Time per analysis:</span>
                      <span className="font-semibold">15 minutes</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-100">Analyses per week:</span>
                      <span className="font-semibold">10-15</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-100">Weekly time spent:</span>
                      <span className="font-semibold">2.5-3.75 hours</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-100">Total cost:</span>
                      <span className="font-semibold text-xl">$99/month</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-8 p-6 bg-white/20 rounded-xl text-center">
                <p className="text-2xl font-bold mb-2">You Save: $2,301+ per month</p>
                <p className="text-green-100">Plus 5x more content output and better quality analysis</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Enhanced Features Section */}
      <section id="features" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4 mb-16">
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Powerful Features</Badge>
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">Everything You Need to Succeed</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Comprehensive tools for stock analysis and content automation
            </p>
          </div>

          <Tabs defaultValue="analysis" className="w-full">
            <TabsList className="grid w-full grid-cols-2 mb-12">
              <TabsTrigger value="analysis" className="text-lg py-3">
                <BarChart3 className="h-5 w-5 mr-2" />
                Stock Analysis
              </TabsTrigger>
              <TabsTrigger value="wordpress" className="text-lg py-3">
                <Globe className="h-5 w-5 mr-2" />
                WordPress Automation
              </TabsTrigger>
            </TabsList>

            <TabsContent value="analysis" className="mt-0">
              <div className="grid lg:grid-cols-2 gap-12 items-center">
                <div>
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <h3 className="text-2xl font-bold text-gray-900">Institutional-Grade Stock Analysis</h3>
                      <p className="text-gray-600">
                        Our AI engine processes millions of data points to deliver comprehensive analysis that rivals
                        top investment firms.
                      </p>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <BarChart3 className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">Advanced Technical Analysis</h4>
                          <p className="text-gray-600">
                            20+ technical indicators including RSI, MACD, Bollinger Bands, Fibonacci retracements,
                            Elliott Wave patterns, and proprietary AI signals. Get clear buy/sell recommendations based
                            on multiple timeframes.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <PieChart className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">Deep Fundamental Analysis</h4>
                          <p className="text-gray-600">
                            Comprehensive evaluation of P/E ratios, EPS growth, revenue trends, profit margins,
                            debt-to-equity, free cash flow, ROE, and competitive positioning. Includes peer comparison
                            and industry benchmarking.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <Shield className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">Comprehensive Risk Assessment</h4>
                          <p className="text-gray-600">
                            Advanced risk metrics including VaR, beta analysis, volatility clustering, downside
                            deviation, maximum drawdown analysis, and stress testing across different market scenarios.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <TrendingUp className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">AI-Powered Price Forecasting</h4>
                          <p className="text-gray-600">
                            Machine learning models trained on 10+ years of data provide price targets with confidence
                            intervals. Includes sentiment analysis from news, social media, and analyst reports.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-gray-900">Sample Analysis Report Structure</h4>
                      <Badge className="bg-green-100 text-green-800">2,847 words</Badge>
                    </div>

                    <div className="space-y-3">
                      <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <FileText className="h-5 w-5 text-green-600" />
                            <span className="font-medium">Executive Summary</span>
                          </div>
                          <span className="text-sm text-gray-500">~300 words</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full">
                          <div className="bg-green-600 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                        </div>
                      </div>

                      <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <LineChart className="h-5 w-5 text-green-600" />
                            <span className="font-medium">Technical Analysis</span>
                          </div>
                          <span className="text-sm text-gray-500">~600 words</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full">
                          <div className="bg-green-600 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                        </div>
                      </div>

                      <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <PieChart className="h-5 w-5 text-green-600" />
                            <span className="font-medium">Fundamental Analysis</span>
                          </div>
                          <span className="text-sm text-gray-500">~500 words</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full">
                          <div className="bg-green-600 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                        </div>
                      </div>

                      <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <Shield className="h-5 w-5 text-green-600" />
                            <span className="font-medium">Risk Assessment</span>
                          </div>
                          <span className="text-sm text-gray-500">~400 words</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full">
                          <div className="bg-green-600 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                        </div>
                      </div>

                      <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <TrendingUp className="h-5 w-5 text-green-600" />
                            <span className="font-medium">Price Forecast & Targets</span>
                          </div>
                          <span className="text-sm text-gray-500">~450 words</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full">
                          <div className="bg-green-600 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                        </div>
                      </div>

                      <div className="p-4 bg-gradient-to-r from-gray-50 to-gray-100 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-3">
                            <BarChart3 className="h-5 w-5 text-green-600" />
                            <span className="font-medium">Investment Recommendation</span>
                          </div>
                          <span className="text-sm text-gray-500">~500 words</span>
                        </div>
                        <div className="w-full bg-gray-200 h-1.5 rounded-full">
                          <div className="bg-green-600 h-1.5 rounded-full" style={{ width: "100%" }}></div>
                        </div>
                      </div>
                    </div>

                    <div className="pt-4 border-t">
                      <Button className="w-full bg-green-600 hover:bg-green-700">
                        <FileText className="h-4 w-4 mr-2" />
                        View Full Sample Report
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="wordpress" className="mt-0">
              <div className="grid lg:grid-cols-2 gap-12 items-center">
                <div>
                  <div className="space-y-6">
                    <div className="space-y-2">
                      <h3 className="text-2xl font-bold text-gray-900">Seamless WordPress Integration</h3>
                      <p className="text-gray-600">
                        Publish professional stock analysis content to multiple WordPress sites with complete automation
                        and customization.
                      </p>
                    </div>

                    <div className="space-y-4">
                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <Globe className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">Multi-Site Management</h4>
                          <p className="text-gray-600">
                            Manage up to 10 WordPress sites from a single dashboard. Configure unique settings,
                            categories, tags, and publishing schedules for each site. Support for WordPress.com,
                            self-hosted, and multisite installations.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <Users className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">Custom Author Profiles</h4>
                          <p className="text-gray-600">
                            Create multiple author personas with unique writing styles, expertise areas, and bios.
                            Perfect for agencies managing content for multiple clients or building authority sites.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <Layers className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">Smart Content Formatting</h4>
                          <p className="text-gray-600">
                            Automatic formatting with H2/H3 headers, bullet points, tables, and embedded charts. SEO
                            optimization with meta descriptions, focus keywords, and schema markup for financial
                            content.
                          </p>
                        </div>
                      </div>

                      <div className="flex items-start space-x-4">
                        <div className="bg-green-100 p-2 rounded-lg mt-1">
                          <Zap className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900">Automated Publishing Workflow</h4>
                          <p className="text-gray-600">
                            Schedule posts for optimal engagement times. Bulk publish to multiple sites simultaneously.
                            Auto-generate featured images with stock charts and branding.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <h4 className="font-semibold text-gray-900">WordPress Publishing Dashboard</h4>
                      <Badge className="bg-green-100 text-green-800">Live Preview</Badge>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                      <div className="flex items-center justify-between mb-4">
                        <span className="font-medium text-gray-700">Site Configuration</span>
                        <Button size="sm" variant="outline">
                          Edit
                        </Button>
                      </div>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Primary Site:</span>
                          <span className="font-medium">InvestmentDaily.com</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Author:</span>
                          <div className="flex items-center space-x-2">
                            <Avatar className="h-6 w-6">
                              <AvatarImage src="/placeholder.svg?height=24&width=24" />
                              <AvatarFallback>JD</AvatarFallback>
                            </Avatar>
                            <span className="font-medium">John Doe</span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Category:</span>
                          <span className="font-medium">Stock Analysis</span>
                        </div>
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Tags:</span>
                          <span className="font-medium">AAPL, Tech Stocks, Analysis</span>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <h5 className="font-medium text-gray-700">Content Sections</h5>
                      <div className="space-y-2">
                        {[
                          "Executive Summary",
                          "Technical Analysis",
                          "Fundamental Analysis",
                          "Risk Assessment",
                          "Price Forecast",
                          "Investment Recommendation",
                          "Disclaimer",
                        ].map((section, index) => (
                          <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                            <div className="flex items-center space-x-2">
                              <CheckCircle className="h-4 w-4 text-green-600" />
                              <span className="text-sm">{section}</span>
                            </div>
                            <button className="text-gray-400 hover:text-gray-600">
                              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M4 6h16M4 12h16M4 18h16"
                                />
                              </svg>
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <Button variant="outline">
                        <Clock className="h-4 w-4 mr-2" />
                        Schedule
                      </Button>
                      <Button className="bg-green-600 hover:bg-green-700">
                        <Newspaper className="h-4 w-4 mr-2" />
                        Publish Now
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-gray-50">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4 mb-16">
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Pricing Plans</Badge>
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">Choose Your Growth Plan</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Start with our 14-day free trial. No credit card required. Cancel anytime.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {/* Starter Plan */}
            <Card className="border-2 hover:border-green-200 transition-colors relative">
              <CardHeader className="space-y-1">
                <CardTitle className="text-2xl">Starter</CardTitle>
                <CardDescription>Perfect for individual investors</CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold">$49</span>
                  <span className="text-gray-500">/month</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Monthly analyses</span>
                    <span className="font-semibold">20</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">WordPress sites</span>
                    <span className="font-semibold">1</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Report length</span>
                    <span className="font-semibold">2,500 words</span>
                  </div>
                </div>
                <div className="border-t pt-4">
                  <ul className="space-y-2">
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Basic technical analysis</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Basic fundamental analysis</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>5-year price history</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Email support</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <X className="h-5 w-5 text-gray-300 shrink-0 mt-0.5" />
                      <span className="text-gray-500">Advanced risk metrics</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <X className="h-5 w-5 text-gray-300 shrink-0 mt-0.5" />
                      <span className="text-gray-500">API access</span>
                    </li>
                  </ul>
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full bg-green-600 hover:bg-green-700">Start Free Trial</Button>
              </CardFooter>
            </Card>

            {/* Professional Plan */}
            <Card className="border-2 border-green-600 shadow-lg relative">
              <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-green-600 text-white px-4 py-1 rounded-full text-sm font-medium">
                Most Popular
              </div>
              <CardHeader className="space-y-1">
                <CardTitle className="text-2xl">Professional</CardTitle>
                <CardDescription>For financial advisors & bloggers</CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold">$99</span>
                  <span className="text-gray-500">/month</span>
                  <div className="text-sm text-green-600 mt-1">Save $120/year with annual billing</div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Monthly analyses</span>
                    <span className="font-semibold">50</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">WordPress sites</span>
                    <span className="font-semibold">3</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Report length</span>
                    <span className="font-semibold">3,000 words</span>
                  </div>
                </div>
                <div className="border-t pt-4">
                  <ul className="space-y-2">
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Advanced technical analysis</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Advanced fundamental analysis</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>10-year price history</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Advanced risk metrics</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Priority email support</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <X className="h-5 w-5 text-gray-300 shrink-0 mt-0.5" />
                      <span className="text-gray-500">API access</span>
                    </li>
                  </ul>
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full bg-green-600 hover:bg-green-700">Start Free Trial</Button>
              </CardFooter>
            </Card>

            {/* Enterprise Plan */}
            <Card className="border-2 hover:border-green-200 transition-colors relative">
              <div className="absolute top-4 right-4">
                <Badge variant="outline" className="border-green-600 text-green-600">
                  <Building2 className="h-3 w-3 mr-1" />
                  Enterprise
                </Badge>
              </div>
              <CardHeader className="space-y-1">
                <CardTitle className="text-2xl">Enterprise</CardTitle>
                <CardDescription>For investment firms & agencies</CardDescription>
                <div className="pt-4">
                  <span className="text-4xl font-bold">$249</span>
                  <span className="text-gray-500">/month</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Monthly analyses</span>
                    <span className="font-semibold text-green-600">Unlimited</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">WordPress sites</span>
                    <span className="font-semibold">10</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Report length</span>
                    <span className="font-semibold">Up to 5,000 words</span>
                  </div>
                </div>
                <div className="border-t pt-4">
                  <ul className="space-y-2">
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Everything in Professional</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>API access</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Custom integrations</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>Dedicated account manager</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>24/7 phone support</span>
                    </li>
                    <li className="flex items-start space-x-3">
                      <CheckCircle className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                      <span>SLA guarantee</span>
                    </li>
                  </ul>
                </div>
              </CardContent>
              <CardFooter>
                <Button className="w-full bg-green-600 hover:bg-green-700">Contact Sales</Button>
              </CardFooter>
            </Card>
          </div>

          <div className="mt-12 text-center">
            <p className="text-gray-600 mb-4">
              Need a custom plan?{" "}
              <Link href="#" className="text-green-600 font-medium hover:text-green-700">
                Contact our sales team
              </Link>{" "}
              for enterprise pricing.
            </p>
            <div className="flex items-center justify-center space-x-6 text-sm text-gray-500">
              <div className="flex items-center space-x-2">
                <Shield className="h-4 w-4" />
                <span>30-day money back guarantee</span>
              </div>
              <div className="flex items-center space-x-2">
                <Lock className="h-4 w-4" />
                <span>Secure payment processing</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-20 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4 mb-16">
            <Badge className="bg-green-100 text-green-800 hover:bg-green-100">FAQ</Badge>
            <h2 className="text-3xl lg:text-4xl font-bold text-gray-900">Frequently Asked Questions</h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Everything you need to know about StockAnalyzer Pro
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <div className="bg-gray-50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">How accurate are the stock analyses?</h3>
              <p className="text-gray-600">
                Our AI models are trained on 10+ years of historical market data and continuously updated with real-time
                information. While no analysis can predict the market with 100% accuracy, our reports provide
                institutional-grade insights that help inform better investment decisions. Our users report a 73%
                improvement in their investment performance.
              </p>
            </div>

            <div className="bg-gray-50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">How does the WordPress integration work?</h3>
              <p className="text-gray-600">
                Simply install our lightweight WordPress plugin on your sites. It creates a secure API connection that
                allows you to publish reports directly from our platform. You maintain full control over formatting,
                categories, tags, and publishing schedules. The entire setup takes less than 5 minutes per site.
              </p>
            </div>

            <div className="bg-gray-50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Can I customize the analysis reports?</h3>
              <p className="text-gray-600">
                You can select which sections to include, adjust the writing tone, add custom introductions and
                conclusions, and even create templates for different types of analyses. Our AI adapts to your
                preferences over time, learning your style and requirements.
              </p>
            </div>

            <div className="bg-gray-50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">What data sources do you use?</h3>
              <p className="text-gray-600">
                We aggregate data from premium financial sources including Bloomberg, Reuters, Yahoo Finance, SEC
                filings, and major exchanges. Our AI also analyzes news sentiment from 1000+ publications and social
                media trends to provide comprehensive market insights.
              </p>
            </div>

            <div className="bg-gray-50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Is there an API for developers?</h3>
              <p className="text-gray-600">
                Yes, our Enterprise plan includes full API access. You can programmatically generate analyses, retrieve
                reports, and integrate our AI engine into your own applications. We provide comprehensive documentation
                and SDKs for popular programming languages.
              </p>
            </div>

            <div className="bg-gray-50 p-6 rounded-xl">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">What happens if I exceed my monthly limit?</h3>
              <p className="text-gray-600">
                You'll receive notifications as you approach your limit. You can either upgrade your plan or purchase
                additional analyses at $5 each. Enterprise customers have unlimited analyses and never need to worry
                about limits.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-br from-green-600 to-green-700">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-3xl mx-auto space-y-8">
            <div className="flex justify-center mb-6">
              <div className="bg-white/20 backdrop-blur-sm rounded-full p-6">
                <DollarSign className="h-16 w-16 text-white" />
              </div>
            </div>
            <h2 className="text-3xl lg:text-4xl font-bold text-white">
              Start Generating Professional Stock Analysis Reports Today
            </h2>
            <p className="text-xl text-green-100">
              Join 500+ financial professionals who are saving 20+ hours per week and delivering better insights to
              their clients.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" className="bg-white text-green-600 hover:bg-gray-100">
                Start 14-Day Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="border-white text-white hover:bg-white hover:text-green-600"
              >
                Schedule Live Demo
              </Button>
            </div>
            <div className="grid grid-cols-3 gap-8 pt-8 max-w-2xl mx-auto">
              <div className="text-center">
                <p className="text-3xl font-bold text-white mb-1">14 days</p>
                <p className="text-sm text-green-200">Free trial period</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-white mb-1">No CC</p>
                <p className="text-sm text-green-200">Required to start</p>
              </div>
              <div className="text-center">
                <p className="text-3xl font-bold text-white mb-1">24/7</p>
                <p className="text-sm text-green-200">Support available</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-5 gap-8">
            <div className="md:col-span-2 space-y-4">
              <div className="flex items-center space-x-2">
                <BarChart3 className="h-6 w-6 text-green-400" />
                <span className="text-lg font-bold">StockAnalyzer Pro</span>
              </div>
              <p className="text-gray-400">
                Professional stock analysis and WordPress automation platform trusted by 500+ financial professionals
                worldwide.
              </p>
              <div className="flex space-x-4">
                <Link href="#" className="text-gray-400 hover:text-white">
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      fillRule="evenodd"
                      d="M22 12c0-5.523-4.477-10-10-10S2 6.477 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987h-2.54V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.89h-2.33v6.988C18.343 21.128 22 16.991 22 12z"
                      clipRule="evenodd"
                    />
                  </svg>
                </Link>
                <Link href="#" className="text-gray-400 hover:text-white">
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
                  </svg>
                </Link>
                <Link href="#" className="text-gray-400 hover:text-white">
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      fillRule="evenodd"
                      d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                      clipRule="evenodd"
                    />
                  </svg>
                </Link>
                <Link href="#" className="text-gray-400 hover:text-white">
                  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path
                      fillRule="evenodd"
                      d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"
                      clipRule="evenodd"
                    />
                  </svg>
                </Link>
              </div>
            </div>
            <div className="space-y-4">
              <h4 className="font-semibold">Product</h4>
              <ul className="space-y-2 text-gray-400">
                <li>
                  <Link href="#features" className="hover:text-white">
                    Features
                  </Link>
                </li>
                <li>
                  <Link href="#pricing" className="hover:text-white">
                    Pricing
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    API Documentation
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Integrations
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Changelog
                  </Link>
                </li>
              </ul>
            </div>
            <div className="space-y-4">
              <h4 className="font-semibold">Resources</h4>
              <ul className="space-y-2 text-gray-400">
                <li>
                  <Link href="#" className="hover:text-white">
                    Blog
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Help Center
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Video Tutorials
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Sample Reports
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Status Page
                  </Link>
                </li>
              </ul>
            </div>
            <div className="space-y-4">
              <h4 className="font-semibold">Company</h4>
              <ul className="space-y-2 text-gray-400">
                <li>
                  <Link href="#" className="hover:text-white">
                    About Us
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Careers
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Contact
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link href="#" className="hover:text-white">
                    Terms of Service
                  </Link>
                </li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <p className="text-gray-400 text-sm">&copy; 2024 StockAnalyzer Pro. All rights reserved.</p>
              <div className="flex items-center space-x-6 mt-4 md:mt-0">
                <div className="flex items-center space-x-2 text-sm text-gray-400">
                  <Lock className="h-4 w-4" />
                  <span>SOC 2 Type II Certified</span>
                </div>
                <div className="flex items-center space-x-2 text-sm text-gray-400">
                  <Shield className="h-4 w-4" />
                  <span>GDPR Compliant</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
