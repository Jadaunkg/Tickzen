import type React from "react"
import ReactApexChart from "react-apexcharts"

interface ChartProps {
  type:
    | "line"
    | "area"
    | "bar"
    | "histogram"
    | "pie"
    | "donut"
    | "radialBar"
    | "scatter"
    | "bubble"
    | "heatmap"
    | "candlestick"
    | "radar"
  series: any[]
  options: any
  width?: string | number
  height?: string | number
}

export const Chart: React.FC<ChartProps> = ({ type, series, options, width, height }) => {
  return <ReactApexChart options={options} series={series} type={type} width={width} height={height} />
}

export const ChartContainer = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>
}

export const ChartTooltip = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>
}

export const ChartTooltipContent = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>
}

export const ChartLegend = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>
}

export const ChartLegendContent = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>
}

export const ChartStyle = ({ children }: { children: React.ReactNode }) => {
  return <div>{children}</div>
}
