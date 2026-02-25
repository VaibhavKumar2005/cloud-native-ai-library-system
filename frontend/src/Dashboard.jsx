import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Shield, Upload, MessageSquare, Activity, FileText } from "lucide-react"
import axios from 'axios'

export default function Dashboard({ onLogout }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [chatHistory, setChatHistory] = useState([])
  const [documents, setDocuments] = useState([])

  const token = localStorage.getItem('access_token')
  const api = axios.create({
    baseURL: 'http://localhost:8000/api/',
    headers: { Authorization: `Bearer ${token}` }
  })

  // 1. Defined first so React knows it exists before useEffect runs
  const fetchDocuments = async () => {
    try {
      const res = await api.get('documents/')
      setDocuments(res.data)
    } catch (err) { 
      console.error("Sync error", err) 
    }
  }

  // 2. Polls the backend every 5 seconds to see if the PDF is done vectorizing
  useEffect(() => {
    fetchDocuments()
    const interval = setInterval(fetchDocuments, 5000) 
    return () => clearInterval(interval)
  }, [])

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', file.name)

    try {
      await api.post('documents/', formData)
      fetchDocuments()
    } catch (err) { 
      console.error("Upload failed", err) 
    }
    setUploading(false)
  }

  const handleQuery = async (e) => {
    e.preventDefault()
    if (!query) return
    setLoading(true)
    try {
      const res = await api.post('query_llm/', { query })
      setChatHistory([{ question: query, ...res.data }, ...chatHistory])
      setQuery('')
    } catch (err) { 
      console.error("AI Error", err) 
    }
    setLoading(false)
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-50 font-sans">
      {/* --- SIDEBAR --- */}
      <div className="w-64 border-r border-slate-800 flex flex-col p-4 bg-slate-900/50">
        <div className="flex items-center gap-3 mb-10 px-2">
          <Shield className="text-indigo-500 w-8 h-8" />
          <span className="font-bold text-lg tracking-tight">VeriRAG</span>
        </div>
        <nav className="flex-1 space-y-2">
          <Button variant="ghost" className="w-full justify-start gap-3 bg-slate-800 text-white">
            <Activity className="w-4 h-4" /> Mission Control
          </Button>
        </nav>
        <Button onClick={onLogout} variant="outline" className="border-slate-700 text-slate-400 hover:bg-red-950 hover:text-red-400">
          End Session
        </Button>
      </div>

      {/* --- MAIN WORKSPACE --- */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT COLUMN: Document Library */}
        <div className="w-80 border-r border-slate-800 p-6 overflow-y-auto bg-slate-950">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-500">Library</h2>
            <Dialog>
              <DialogTrigger asChild>
                <Button size="sm" className="bg-indigo-600 hover:bg-indigo-700">
                  <Upload className="w-4 h-4 mr-2" /> Add PDF
                </Button>
              </DialogTrigger>
              <DialogContent className="bg-slate-900 border-slate-800 text-white">
                <DialogHeader><DialogTitle>Ingest New Document</DialogTitle></DialogHeader>
                <div className="py-4">
                   <Input type="file" accept=".pdf" onChange={handleFileUpload} className="bg-slate-950 border-slate-800" />
                   {uploading && <p className="text-xs text-indigo-400 mt-2 animate-pulse">Uploading to Database...</p>}
                </div>
              </DialogContent>
            </Dialog>
          </div>
          
          <div className="space-y-3">
            {documents.length === 0 && <p className="text-xs text-slate-500 text-center py-8">Vault is empty.</p>}
            {documents.map(doc => (
              <Card key={doc.id} className="bg-slate-900/50 border-slate-800">
                <CardContent className="p-3 flex items-start gap-3">
                  <FileText className="w-5 h-5 text-indigo-400 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{doc.title}</p>
                    <p className={`text-[10px] mt-1 font-bold ${doc.processed ? 'text-emerald-500' : 'text-amber-500'}`}>
                      {doc.processed ? '● INDEXED' : '○ PROCESSING'}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* RIGHT COLUMN: AI Terminal */}
        <div className="flex-1 flex flex-col bg-slate-900/20">
          <div className="flex-1 p-8 overflow-y-auto space-y-8">
            {chatHistory.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 italic">
                <MessageSquare className="w-12 h-12 mb-4 opacity-20" />
                <p>Awaiting your query. Responses are strictly verified against the library.</p>
              </div>
            )}
            
            {chatHistory.map((chat, i) => (
              <div key={i}>
                <div className="flex justify-end mb-4">
                  <div className="bg-indigo-600 px-4 py-2 rounded-2xl rounded-tr-none max-w-md">
                    {chat.question}
                  </div>
                </div>
                <Card className="bg-slate-900 border-slate-800 border-l-4 border-l-emerald-500">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-[10px] font-mono tracking-widest text-emerald-500 uppercase flex items-center gap-2">
                      <Shield className="w-3 h-3" /> Integrity Verified Response
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-slate-200 text-sm leading-relaxed">{chat.answer}</p>
                    
                    <div className="space-y-2 pt-2 border-t border-slate-800">
                      <div className="flex justify-between text-[10px] font-mono text-slate-500">
                        <span>Faithfulness Confidence</span>
                        <span className="text-emerald-400">{(chat.faithfulness_score * 100).toFixed(0)}%</span>
                      </div>
                      <Progress value={chat.faithfulness_score * 100} className="h-1 bg-slate-800" />
                    </div>

                    {chat.source_citation && chat.source_citation !== "None" && (
                      <div className="p-3 bg-slate-950/50 rounded border border-slate-800/50 text-[11px] italic text-slate-400">
                        "{chat.source_citation}"
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            ))}
          </div>

          {/* AI Terminal Input */}
          <div className="p-8 bg-slate-950/50 border-t border-slate-800">
            <form onSubmit={handleQuery} className="flex gap-4 max-w-4xl mx-auto">
              <Input 
                placeholder="Ask VeriRAG Librarian..." 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="bg-slate-900 border-slate-800 h-12 text-slate-100 placeholder:text-slate-500"
              />
              <Button type="submit" disabled={loading} className="h-12 px-8 bg-indigo-600 hover:bg-indigo-700">
                {loading ? "Verifying..." : "Query AI"}
              </Button>
            </form>
          </div>
          
        </div>
      </div>
    </div>
  )
}