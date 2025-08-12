"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"

interface Event {
  name: string
  start_date: string
  end_date: string
  location: string
  url: string
}

export default function TFBDMap() {
  const [events, setEvents] = useState<Event[]>([])
  const [filteredEvents, setFilteredEvents] = useState<Event[]>([])
  const [filtersExpanded, setFiltersExpanded] = useState(true)
  const [filters, setFilters] = useState({
    name: "",
    start_date: "",
    end_date: "",
    location: "",
    url: "",
  })
  const [backgroundImage, setBackgroundImage] = useState("/images/dancer-background.png")

  useEffect(() => {
    // Load events data
    fetch("/events.json")
      .then((res) => res.json())
      .then((data) => {
        setEvents(data)
        setFilteredEvents(data)
      })
      .catch((err) => console.error("Error loading events:", err))
  }, [])

  useEffect(() => {
    // Apply filters
    const filtered = events.filter((event) => {
      return (
        event.name.toLowerCase().includes(filters.name.toLowerCase()) &&
        event.start_date.includes(filters.start_date) &&
        event.end_date.includes(filters.end_date) &&
        event.location.toLowerCase().includes(filters.location.toLowerCase()) &&
        event.url.toLowerCase().includes(filters.url.toLowerCase())
      )
    })
    setFilteredEvents(filtered)
  }, [filters, events])

  const handleFilterChange = (field: keyof typeof filters, value: string) => {
    setFilters((prev) => ({ ...prev, [field]: value }))
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Fixed Background Image */}
      <div
        className="fixed inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      />

      {/* Gradient Overlay */}
      <div className="fixed inset-0 bg-gradient-to-br from-pink-200/30 via-rose-100/20 to-orange-200/30" />

      {/* Header */}
      <header className="relative z-10 flex justify-between items-center p-6">
        <h1 className="text-4xl font-bold text-white drop-shadow-lg font-serif">tfbd Map</h1>

        {/* Telegram Button */}
        <Button
          asChild
          className="bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 text-white shadow-lg backdrop-blur-sm border border-white/20"
        >
          <a href="https://t.me/TFBDMap" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
            <img src="/images/telegram-icon.png" alt="Telegram" className="w-5 h-5" />
            Join the community
          </a>
        </Button>
      </header>

      {/* Main Content - Floating Table */}
      <main className="relative z-10 px-6 pb-6">
        <Card className="bg-white/10 backdrop-blur-md border-white/20 shadow-2xl max-h-[70vh] overflow-hidden">
          {/* Filters */}
          <div className="border-b border-white/20">
            {/* Collapsible header with toggle button */}
            <div className="p-4 flex justify-between items-center">
              <h3 className="text-white font-semibold">Filters</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setFiltersExpanded(!filtersExpanded)}
                className="text-white hover:bg-white/20 p-2"
              >
                <svg
                  className={`w-4 h-4 transition-transform ${filtersExpanded ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Button>
            </div>

            <div
              className={`overflow-hidden transition-all duration-300 ${filtersExpanded ? "max-h-96 pb-4" : "max-h-0"}`}
            >
              <div className="px-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                  <Input
                    placeholder="Filter by event name..."
                    value={filters.name}
                    onChange={(e) => handleFilterChange("name", e.target.value)}
                    className="bg-white/20 border-white/30 text-white placeholder:text-white/70 backdrop-blur-sm"
                  />
                  <Input
                    placeholder="Filter by start date..."
                    value={filters.start_date}
                    onChange={(e) => handleFilterChange("start_date", e.target.value)}
                    className="bg-white/20 border-white/30 text-white placeholder:text-white/70 backdrop-blur-sm"
                  />
                  <Input
                    placeholder="Filter by end date..."
                    value={filters.end_date}
                    onChange={(e) => handleFilterChange("end_date", e.target.value)}
                    className="bg-white/20 border-white/30 text-white placeholder:text-white/70 backdrop-blur-sm"
                  />
                  <Input
                    placeholder="Filter by location..."
                    value={filters.location}
                    onChange={(e) => handleFilterChange("location", e.target.value)}
                    className="bg-white/20 border-white/30 text-white placeholder:text-white/70 backdrop-blur-sm"
                  />
                  <Input
                    placeholder="Filter by URL..."
                    value={filters.url}
                    onChange={(e) => handleFilterChange("url", e.target.value)}
                    className="bg-white/20 border-white/30 text-white placeholder:text-white/70 backdrop-blur-sm"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-auto max-h-96">
            <table className="w-full">
              <thead className="sticky top-0 bg-white/20 backdrop-blur-sm">
                <tr className="border-b border-white/20">
                  <th className="text-left p-4 text-white font-semibold">Event Name</th>
                  <th className="text-left p-4 text-white font-semibold">Start Date</th>
                  <th className="text-left p-4 text-white font-semibold">End Date</th>
                  <th className="text-left p-4 text-white font-semibold">Location</th>
                  <th className="text-left p-4 text-white font-semibold">URL</th>
                </tr>
              </thead>
              <tbody>
                {filteredEvents.map((event, index) => (
                  <tr key={index} className="border-b border-white/10 hover:bg-white/10 transition-colors">
                    <td className="p-4 text-white">{event.name}</td>
                    <td className="p-4 text-white">{event.start_date}</td>
                    <td className="p-4 text-white">{event.end_date}</td>
                    <td className="p-4 text-white">{event.location}</td>
                    <td className="p-4">
                      <a
                        href={event.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-pink-200 hover:text-pink-100 underline transition-colors"
                      >
                        Visit Event
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredEvents.length === 0 && (
              <div className="p-8 text-center text-white/70">No events found matching your filters.</div>
            )}
          </div>
        </Card>
      </main>
    </div>
  )
}
