import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Switch } from '@/components/ui/switch.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { 
  Download, 
  Video, 
  FileText, 
  Settings, 
  Calendar, 
  History,
  Palette,
  Wifi,
  Bell,
  FolderOpen,
  RotateCcw,
  Play,
  Pause,
  Trash2,
  Share2
} from 'lucide-react'
import './App.css'

// API base URL
const API_BASE = 'http://localhost:5000/api'

function App() {
  const [downloads, setDownloads] = useState([])
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    completed: 0,
    total_size: 0,
    avg_speed: 0
  })
  const [activeFilter, setActiveFilter] = useState('all')
  const [settings, setSettings] = useState({
    autoStart: true,
    parallelDownloads: true,
    notifications: true,
    autoOrganize: false,
    autoRetry: true,
    extractSubtitles: false
  })
  const [downloadUrl, setDownloadUrl] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  // Fetch downloads and stats from backend
  const fetchDownloads = async () => {
    try {
      const response = await fetch(`${API_BASE}/download/list`)
      if (response.ok) {
        const data = await response.json()
        setDownloads(data)
      }
    } catch (error) {
      console.error('Error fetching downloads:', error)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/download/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Error fetching stats:', error)
    }
  }

  // Start a new download
  const startDownload = async (url) => {
    if (!url.trim()) return

    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/download/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: url.trim() })
      })

      if (response.ok) {
        const data = await response.json()
        console.log('Download started:', data)
        setDownloadUrl('')
        fetchDownloads()
        fetchStats()
      } else {
        const error = await response.json()
        console.error('Error starting download:', error)
      }
    } catch (error) {
      console.error('Error starting download:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Pause a download
  const pauseDownload = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/download/pause/${taskId}`, {
        method: 'POST'
      })
      if (response.ok) {
        fetchDownloads()
        fetchStats()
      }
    } catch (error) {
      console.error('Error pausing download:', error)
    }
  }

  // Resume a download
  const resumeDownload = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/download/resume/${taskId}`, {
        method: 'POST'
      })
      if (response.ok) {
        fetchDownloads()
        fetchStats()
      }
    } catch (error) {
      console.error('Error resuming download:', error)
    }
  }

  // Delete a download
  const deleteDownload = async (taskId) => {
    try {
      const response = await fetch(`${API_BASE}/download/delete/${taskId}`, {
        method: 'DELETE'
      })
      if (response.ok) {
        fetchDownloads()
        fetchStats()
      }
    } catch (error) {
      console.error('Error deleting download:', error)
    }
  }

  // Retry a download
  const retryDownload = async (taskId) => {
    const taskToRetry = downloads.find(d => d.id === taskId);
    if (taskToRetry) {
      // First, delete the old failed task from the backend
      await deleteDownload(taskId);
      // Then, start a new download with the same URL
      await startDownload(taskToRetry.url);
    }
  };


  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // Format speed
  const formatSpeed = (bytesPerSecond) => {
    if (bytesPerSecond === 0) return '0 B/s'
    return formatFileSize(bytesPerSecond) + '/s'
  }

  // Paste from clipboard
  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText()
      setDownloadUrl(text)
    } catch (error) {
      console.error('Error reading clipboard:', error)
    }
  }

  // Filter downloads
  const filteredDownloads = downloads.filter(download => {
    if (activeFilter === 'all') return true
    if (activeFilter === 'video') return download.filename.match(/\.(mp4|avi|mkv|mov|wmv)$/i)
    if (activeFilter === 'documents') return download.filename.match(/\.(pdf|doc|docx|txt|rtf)$/i)
    if (activeFilter === 'programs') return download.filename.match(/\.(exe|msi|dmg|pkg)$/i)
    if (activeFilter === 'completed') return download.status === 'completed'
    return true
  })

  // Auto-refresh downloads and stats
  useEffect(() => {
    fetchDownloads()
    fetchStats()
    
    const interval = setInterval(() => {
      fetchDownloads()
      fetchStats()
    }, 2000) // Refresh every 2 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-900 dark:to-gray-800 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg flex items-center justify-center">
                    <Download className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white">DownloadMaster</h1>
                    <p className="text-gray-600 dark:text-gray-300">Modern Download Manager</p>
                  </div>
                </div>
                <div className="flex items-center space-x-6">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">{stats.total}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">QUEUE</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{stats.active}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">ACTIVE</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">DONE</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Content Area */}
          <div className="lg:col-span-3 space-y-6">
            {/* Input Card */}
            <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
              <CardContent className="p-6">
                <Tabs defaultValue="single" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="single">Single File</TabsTrigger>
                    <TabsTrigger value="video">Video/Playlist</TabsTrigger>
                    <TabsTrigger value="torrent">Torrent</TabsTrigger>
                    <TabsTrigger value="bulk">Bulk Download</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="single" className="space-y-4">
                    <div className="flex space-x-2">
                      <Input 
                        placeholder="Paste your URL here..." 
                        className="flex-1"
                        value={downloadUrl}
                        onChange={(e) => setDownloadUrl(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && startDownload(downloadUrl)}
                      />
                      <Button variant="outline" size="sm" onClick={pasteFromClipboard}>
                        <FileText className="w-4 h-4 mr-1" />
                        Paste
                      </Button>
                      <Button 
                        className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600"
                        onClick={() => startDownload(downloadUrl)}
                        disabled={isLoading || !downloadUrl.trim()}
                      >
                        <Download className="w-4 h-4 mr-2" />
                        {isLoading ? 'Starting...' : 'Download'}
                      </Button>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="video" className="space-y-4">
                    <div className="flex space-x-2">
                      <Input 
                        placeholder="Paste video URL here..." 
                        className="flex-1"
                      />
                      <Button variant="outline" size="sm">
                        <FileText className="w-4 h-4 mr-1" />
                        Paste
                      </Button>
                      <Button variant="outline">
                        <Video className="w-4 h-4 mr-2" />
                        Analyze
                      </Button>
                    </div>
                    <div className="grid grid-cols-3 gap-4 mt-4">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Video Quality</label>
                        <select className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                          <option>Best Available</option>
                          <option>1080p</option>
                          <option>720p</option>
                          <option>480p</option>
                          <option>360p</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Format</label>
                        <select className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                          <option>MP4</option>
                          <option>WebM</option>
                          <option>AVI</option>
                          <option>MKV</option>
                          <option>Audio Only (MP3)</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Save Location</label>
                        <div className="flex mt-1">
                          <Input 
                            placeholder="Downloads/Videos" 
                            className="flex-1 rounded-r-none"
                          />
                          <Button variant="outline" className="rounded-l-none border-l-0">
                            <FolderOpen className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="torrent" className="space-y-4">
                    <div className="flex space-x-2">
                      <Input 
                        placeholder="Paste magnet link or upload .torrent file..." 
                        className="flex-1"
                      />
                      <Button variant="outline" size="sm">
                        <FileText className="w-4 h-4 mr-1" />
                        Paste
                      </Button>
                      <Button variant="outline">
                        <FolderOpen className="w-4 h-4 mr-2" />
                        Browse
                      </Button>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Download Path</label>
                        <div className="flex mt-1">
                          <Input 
                            placeholder="Downloads/Torrents" 
                            className="flex-1 rounded-r-none"
                          />
                          <Button variant="outline" className="rounded-l-none border-l-0">
                            <FolderOpen className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Max Connections</label>
                        <select className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                          <option>Auto</option>
                          <option>50</option>
                          <option>100</option>
                          <option>200</option>
                          <option>Unlimited</option>
                        </select>
                      </div>
                    </div>
                  </TabsContent>
                  
                  <TabsContent value="bulk" className="space-y-4">
                    <div className="space-y-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                          Multiple URLs (one per line) or URL Pattern
                        </label>
                        <div className="flex space-x-2">
                          <textarea 
                            placeholder="Option 1 - Multiple URLs:&#10;https://example.com/file1.zip&#10;https://example.com/file2.zip&#10;https://example.com/file3.zip&#10;&#10;Option 2 - URL Pattern:&#10;https://example.com/file[01-50].zip&#10;https://site.com/image[001-100].jpg"
                            className="flex-1 min-h-[120px] p-3 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white resize-none"
                          />
                          <div className="flex flex-col space-y-2">
                            <Button variant="outline" size="sm">
                              <FileText className="w-4 h-4 mr-1" />
                              Paste
                            </Button>
                            <Button variant="outline" size="sm">
                              <FolderOpen className="w-4 h-4 mr-1" />
                              Import
                            </Button>
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Download Path</label>
                          <div className="flex mt-1">
                            <Input 
                              placeholder="Downloads/Bulk" 
                              className="flex-1 rounded-r-none"
                            />
                            <Button variant="outline" className="rounded-l-none border-l-0">
                              <FolderOpen className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                        <div>
                          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Concurrent Downloads</label>
                          <select className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                            <option>3</option>
                            <option>5</option>
                            <option>10</option>
                            <option>Unlimited</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">Delay Between Downloads</label>
                          <select className="w-full mt-1 p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                            <option>No Delay</option>
                            <option>1 Second</option>
                            <option>5 Seconds</option>
                            <option>10 Seconds</option>
                          </select>
                        </div>
                      </div>
                      <div className="flex space-x-2">
                        <Button variant="outline" className="flex-1">
                          <Download className="w-4 h-4 mr-2" />
                          Preview URLs
                        </Button>
                        <Button className="flex-1 bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600">
                          <Download className="w-4 h-4 mr-2" />
                          Start Bulk Download
                        </Button>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>

            {/* Downloads List */}
            <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-xl font-semibold">Downloads</CardTitle>
                  <div className="flex space-x-2">
                    {['all', 'video', 'documents', 'programs', 'completed'].map((filter) => (
                      <Badge 
                        key={filter}
                        variant={activeFilter === filter ? "default" : "outline"}
                        className="cursor-pointer capitalize"
                        onClick={() => setActiveFilter(filter)}
                      >
                        {filter}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {filteredDownloads.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <div className="text-4xl mb-4">📥</div>
                      <p>No downloads yet. Start by adding a URL above!</p>
                    </div>
                  ) : (
                    filteredDownloads.map((download) => (
                      <div key={download.id} className="bg-white rounded-xl shadow-md p-4 border border-gray-100 hover:shadow-lg transition-shadow">
                        <div className="flex items-start gap-4">
                          {/* Thumbnail/Icon */}
                          <div className="flex-shrink-0">
                            <div className="w-16 h-12 bg-gradient-to-br from-purple-100 to-blue-100 rounded-lg flex items-center justify-center relative overflow-hidden">
                              {download.type === 'video' ? (
                                <div className="text-purple-600 text-lg">🎥</div>
                              ) : download.type === 'audio' ? (
                                <div className="text-blue-600 text-lg">🎵</div>
                              ) : download.type === 'torrent' ? (
                                <div className="text-green-600 text-lg">🌐</div>
                              ) : (
                                <div className="text-gray-600 text-lg">📄</div>
                              )}
                              {download.status === 'downloading' && (
                                <div className="absolute bottom-0 right-0 bg-blue-500 text-white text-xs px-1 rounded-tl">
                                  {Math.round(download.progress)}%
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            {/* Title and Info */}
                            <div className="mb-2">
                              <h3 className="font-medium text-gray-900 truncate text-sm">
                                {download.title || (download.filename ? download.filename.split('\\').pop().split('/').pop() : download.url?.split('/').pop()) || 'Unknown File'}
                              </h3>
                              <div className="flex items-center gap-2 text-xs text-gray-500 mt-1">
                                <span className="flex items-center gap-1">
                                  👤 {download.source || 'Direct Download'}
                                </span>
                                <span>•</span>
                                <span className="flex items-center gap-1">
                                  ⏱️ {download.duration || formatFileSize(download.total_size)}
                                </span>
                              </div>
                            </div>

                            {/* Progress Bar */}
                            <div className="mb-3">
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span className={`font-medium ${
                                  download.status === 'completed' ? 'text-green-600' :
                                  download.status === 'error' ? 'text-red-600' :
                                  download.status === 'paused' ? 'text-yellow-600' :
                                  'text-blue-600'
                                }`}>
                                  {download.status === 'completed' ? 'Completed' :
                                   download.status === 'error' ? 'Error' :
                                   download.status === 'paused' ? 'Paused' :
                                   'Downloading'}
                                </span>
                                <span className="text-gray-500">
                                  {download.status === 'downloading' ? formatSpeed(download.speed) : ''}
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className={`h-2 rounded-full transition-all duration-300 ${
                                    download.status === 'completed' ? 'bg-green-500' :
                                    download.status === 'error' ? 'bg-red-500' :
                                    download.status === 'paused' ? 'bg-yellow-500' :
                                    'bg-blue-500'
                                  }`}
                                  style={{ width: `${download.progress}%` }}
                                ></div>
                              </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-2">
                              {download.status === 'completed' && (
                                <>
                                  <button className="p-2 bg-green-100 text-green-700 text-xs rounded-lg hover:bg-green-200 transition-colors flex items-center gap-1.5">
                                    <Play size={14} /> Play
                                  </button>
                                  <button className="p-2 bg-blue-100 text-blue-700 text-xs rounded-lg hover:bg-blue-200 transition-colors flex items-center gap-1.5">
                                    <FolderOpen size={14} /> Open
                                  </button>
                                  <button className="p-2 bg-purple-100 text-purple-700 text-xs rounded-lg hover:bg-purple-200 transition-colors flex items-center gap-1.5">
                                    <Share2 size={14} /> Share
                                  </button>
                                </>
                              )}
                              
                              {download.status === 'downloading' && (
                                <>
                                  <button 
                                    onClick={() => pauseDownload(download.id)}
                                    className="p-2 bg-yellow-100 text-yellow-700 text-xs rounded-lg hover:bg-yellow-200 transition-colors flex items-center gap-1.5"
                                  >
                                    <Pause size={14} /> Pause
                                  </button>
                                  <button 
                                    onClick={() => deleteDownload(download.id)}
                                    className="p-2 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 transition-colors flex items-center gap-1.5"
                                  >
                                    <Trash2 size={14} /> Cancel
                                  </button>
                                </>
                              )}
                              
                              {download.status === 'paused' && (
                                <>
                                  <button 
                                    onClick={() => resumeDownload(download.id)}
                                    className="p-2 bg-green-100 text-green-700 text-xs rounded-lg hover:bg-green-200 transition-colors flex items-center gap-1.5"
                                  >
                                    <Play size={14} /> Resume
                                  </button>
                                  <button 
                                    onClick={() => deleteDownload(download.id)}
                                    className="p-2 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 transition-colors flex items-center gap-1.5"
                                  >
                                    <Trash2 size={14} /> Cancel
                                  </button>
                                </>
                              )}
                              
                              {download.status === 'error' && (
                                <>
                                  <button 
                                    onClick={() => retryDownload(download.id)}
                                    className="p-2 bg-blue-100 text-blue-700 text-xs rounded-lg hover:bg-blue-200 transition-colors flex items-center gap-1.5"
                                  >
                                    <RotateCcw size={14} /> Retry
                                  </button>
                                  <button 
                                    onClick={() => deleteDownload(download.id)}
                                    className="p-2 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 transition-colors flex items-center gap-1.5"
                                  >
                                    <Trash2 size={14} /> Delete
                                  </button>
                                </>
                              )}
                              
                              {/* Always show delete for completed downloads */}
                              {download.status === 'completed' && (
                                <button
                                  onClick={() => deleteDownload(download.id)}
                                  className="p-2 bg-red-100 text-red-700 text-xs rounded-lg hover:bg-red-200 transition-colors flex items-center gap-1.5 ml-auto"
                                >
                                  <Trash2 size={14} />
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Sidebar */}
        <div className="flex-1 space-y-6">
          {/* Statistics */}
          <div className="bg-white rounded-xl shadow-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 text-xs">📊</span>
              </div>
              <h3 className="text-base font-semibold text-gray-800">Stats</h3>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-purple-50 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-purple-600">{stats.total}</div>
                <div className="text-xs text-gray-600">Total</div>
              </div>
              <div className="bg-blue-50 rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-blue-600">{stats.active}</div>
                <div className="text-xs text-gray-600">Active</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="bg-green-50 rounded-lg p-2 text-center">
                <div className="text-sm font-bold text-green-600">{formatFileSize(stats.total_size)}</div>
                <div className="text-xs text-gray-600">Size</div>
              </div>
              <div className="bg-orange-50 rounded-lg p-2 text-center">
                <div className="text-sm font-bold text-orange-600">{formatSpeed(stats.avg_speed)}</div>
                <div className="text-xs text-gray-600">Speed</div>
              </div>
            </div>
            <div className="mt-3 bg-green-100 rounded-lg p-2 text-center">
              <div className="text-xs font-medium text-green-700">Unlimited available</div>
            </div>
          </div>

            {/* Quick Settings Card */}
            <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Settings className="w-5 h-5" />
                  <span>Quick Settings</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {Object.entries(settings).map(([key, value]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="text-sm capitalize">
                      {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                    </span>
                    <Switch 
                      checked={value}
                      onCheckedChange={(checked) => 
                        setSettings(prev => ({ ...prev, [key]: checked }))
                      }
                    />
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Additional Features Card */}
            <Card className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <div className="w-5 h-5 bg-gradient-to-r from-green-500 to-teal-500 rounded"></div>
                  <span>Additional Features</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <Calendar className="w-3 h-3" />
                    <span className="text-xs">Schedule</span>
                  </Button>
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <FileText className="w-3 h-3" />
                    <span className="text-xs">Converter</span>
                  </Button>
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <History className="w-3 h-3" />
                    <span className="text-xs">History</span>
                  </Button>
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <Wifi className="w-3 h-3" />
                    <span className="text-xs">Bandwidth</span>
                  </Button>
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <Video className="w-3 h-3" />
                    <span className="text-xs">Metadata</span>
                  </Button>
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <Palette className="w-3 h-3" />
                    <span className="text-xs">Themes</span>
                  </Button>
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <RotateCcw className="w-3 h-3" />
                    <span className="text-xs">Backup</span>
                  </Button>
                  <Button variant="outline" size="sm" className="flex items-center space-x-1">
                    <Download className="w-3 h-3" />
                    <span className="text-xs">Updates</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
