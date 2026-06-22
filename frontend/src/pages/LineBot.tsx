import { useState, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  MessageCircle, Send, Bot, User, CheckCircle2, XCircle,
  Settings, Send as SendIcon, Copy, Webhook, RefreshCw,
} from 'lucide-react'
import {
  getLineStatus, getLineCommands, simulateLine,
  getLineConfig, setLineConfig, pushLineDaily,
} from '../api'

interface ChatMsg {
  from: 'user' | 'bot'
  text: string
  quick?: string[]
}

export default function LineBot() {
  const qc = useQueryClient()
  const { data: status } = useQuery({ queryKey: ['line-status'], queryFn: getLineStatus, refetchInterval: 15000 })
  const { data: commands } = useQuery({ queryKey: ['line-commands'], queryFn: getLineCommands })
  const { data: config } = useQuery({ queryKey: ['line-config'], queryFn: getLineConfig })

  const [messages, setMessages] = useState<ChatMsg[]>([
    { from: 'bot', text: 'สวัสดีครับ 🙏 ลองพิมพ์ "ช่วยเหลือ" หรือกดปุ่มเมนูเพื่อเริ่มใช้งานได้เลย', quick: ['ช่วยเหลือ', 'สรุป', 'วันนี้'] },
  ])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const chatEnd = useRef<HTMLDivElement>(null)

  const [recipient, setRecipient] = useState('')
  useEffect(() => { if (config?.default_to !== undefined) setRecipient(config.default_to) }, [config])
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (text: string) => {
    const t = text.trim()
    if (!t || sending) return
    setInput('')
    setMessages(m => [...m, { from: 'user', text: t }])
    setSending(true)
    try {
      const res = await simulateLine(t)
      setMessages(m => [...m, { from: 'bot', text: res.reply, quick: res.quick_replies }])
    } catch {
      setMessages(m => [...m, { from: 'bot', text: '⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ' }])
    } finally {
      setSending(false)
    }
  }

  const saveConfig = useMutation({
    mutationFn: () => setLineConfig(recipient),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['line-config'] }),
  })

  const [pushResult, setPushResult] = useState<any>(null)
  const doPush = useMutation({
    mutationFn: pushLineDaily,
    onSuccess: (r) => setPushResult(r),
  })

  const webhookUrl = `${window.location.origin}/api/line/webhook`

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <MessageCircle className="w-6 h-6 text-green-600" /> LINE Bot
        </h1>
        <p className="text-gray-500 text-sm mt-1">
          บอทผู้ช่วยสำนักงานบัญชี — ทดสอบได้ทันทีในหน้านี้ และเชื่อมต่อ LINE จริงเมื่อพร้อม
        </p>
      </div>

      {/* Status banner */}
      <div className={`card p-4 flex items-center gap-3 ${status?.configured ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
        {status?.configured
          ? <CheckCircle2 className="w-5 h-5 text-green-600 shrink-0" />
          : <XCircle className="w-5 h-5 text-amber-600 shrink-0" />}
        <div className="text-sm">
          {status?.configured ? (
            <span className="text-green-800">เชื่อมต่อ LINE แล้ว — บอทพร้อมตอบในแอป LINE จริง</span>
          ) : (
            <span className="text-amber-800">
              ยังไม่ได้ตั้งค่า LINE token — ยังทดสอบในหน้านี้ได้เต็มรูปแบบ (โหมดจำลอง)
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chat simulator */}
        <div className="lg:col-span-2 card flex flex-col h-[560px] overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2 bg-gray-50">
            <Bot className="w-4 h-4 text-green-600" />
            <span className="font-semibold text-sm">แชทจำลอง (Simulator)</span>
            <span className="badge-gray ml-auto">เชื่อมต่อข้อมูลจริง</span>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#8aabd3]/10">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.from === 'user' ? 'justify-end' : 'justify-start'}`}>
                {m.from === 'bot' && <div className="w-7 h-7 rounded-full bg-green-500 flex items-center justify-center shrink-0"><Bot className="w-4 h-4 text-white" /></div>}
                <div className="max-w-[78%]">
                  <div className={`px-3 py-2 rounded-2xl text-sm whitespace-pre-wrap break-words ${
                    m.from === 'user' ? 'bg-green-500 text-white rounded-br-sm' : 'bg-white border border-gray-200 rounded-bl-sm'
                  }`}>
                    {m.text}
                  </div>
                  {m.quick && m.quick.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {m.quick.map(q => (
                        <button key={q} onClick={() => send(q)}
                          className="px-3 py-1 text-xs rounded-full border border-green-400 text-green-700 bg-white hover:bg-green-50 transition-colors">
                          {q}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                {m.from === 'user' && <div className="w-7 h-7 rounded-full bg-gray-400 flex items-center justify-center shrink-0"><User className="w-4 h-4 text-white" /></div>}
              </div>
            ))}
            {sending && <div className="text-xs text-gray-400 ml-9">บอทกำลังพิมพ์...</div>}
            <div ref={chatEnd} />
          </div>

          <div className="p-3 border-t border-gray-100 flex gap-2">
            <input
              className="input"
              placeholder='พิมพ์ข้อความ เช่น "สรุป" หรือ "ลูกค้า AC001"'
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') send(input) }}
            />
            <button onClick={() => send(input)} disabled={sending}
              className="btn-primary flex items-center gap-1 shrink-0 disabled:opacity-50">
              <Send className="w-4 h-4" /> ส่ง
            </button>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Commands */}
          <div className="card p-4">
            <h2 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <MessageCircle className="w-4 h-4 text-indigo-600" /> คำสั่งที่ใช้ได้
            </h2>
            <div className="space-y-2">
              {commands?.commands.map((c: any) => (
                <button key={c.command} onClick={() => send(c.command.split(' ')[0])}
                  className="w-full text-left p-2 rounded-lg hover:bg-gray-50 transition-colors">
                  <div className="text-sm font-medium text-gray-800">{c.command}</div>
                  <div className="text-xs text-gray-500">{c.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Daily digest */}
          <div className="card p-4">
            <h2 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <SendIcon className="w-4 h-4 text-green-600" /> แจ้งเตือนรายวัน
            </h2>
            <p className="text-xs text-gray-500 mb-3">
              ระบบจะส่งสรุปประจำวันอัตโนมัติทุกวัน 08:30 น. ไปยังปลายทางด้านล่าง (ต้องตั้งค่า token ก่อน)
            </p>
            <label className="label">User ID / Group ID ปลายทาง</label>
            <input className="input mb-2" placeholder="Uxxxxxxxx... หรือ Cxxxxxxxx..."
              value={recipient} onChange={e => setRecipient(e.target.value)} />
            <div className="flex gap-2">
              <button onClick={() => saveConfig.mutate()} className="btn-secondary flex-1 flex items-center justify-center gap-1">
                <Settings className="w-4 h-4" /> {saveConfig.isPending ? 'บันทึก...' : 'บันทึก'}
              </button>
              <button onClick={() => doPush.mutate()} className="btn-success flex-1 flex items-center justify-center gap-1">
                {doPush.isPending ? <RefreshCw className="w-4 h-4 animate-spin" /> : <SendIcon className="w-4 h-4" />} ส่งทดสอบ
              </button>
            </div>
            {saveConfig.isSuccess && <div className="text-xs text-green-600 mt-2">✓ บันทึกแล้ว</div>}
            {pushResult && (
              <div className={`text-xs mt-2 p-2 rounded ${pushResult.sent ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'}`}>
                {pushResult.sent ? '✓ ส่งเข้า LINE สำเร็จ' : `ยังไม่ได้ส่ง: ${pushResult.reason || 'ตรวจสอบ token/ผู้รับ'}`}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Setup guide */}
      <div className="card p-5">
        <h2 className="font-semibold mb-3 flex items-center gap-2">
          <Webhook className="w-5 h-5 text-indigo-600" /> วิธีเชื่อมต่อ LINE จริง (ทำครั้งเดียว)
        </h2>
        <ol className="text-sm text-gray-600 space-y-2 list-decimal list-inside">
          <li>สร้าง <b>Messaging API channel</b> ที่ <a className="text-indigo-600 underline" href="https://developers.line.biz" target="_blank" rel="noreferrer">developers.line.biz</a></li>
          <li>คัดลอก <b>Channel access token</b> และ <b>Channel secret</b> ไปตั้งเป็น environment variable:
            <pre className="bg-gray-900 text-gray-100 text-xs rounded-lg p-3 mt-1 overflow-x-auto">{`export LINE_CHANNEL_ACCESS_TOKEN="<token>"
export LINE_CHANNEL_SECRET="<secret>"`}</pre>
          </li>
          <li>ตั้งค่า <b>Webhook URL</b> ในคอนโซล LINE เป็น:
            <div className="flex items-center gap-2 mt-1">
              <code className="bg-gray-100 px-2 py-1 rounded text-xs flex-1 break-all">{webhookUrl}</code>
              <button onClick={() => navigator.clipboard.writeText(webhookUrl)} className="btn-secondary flex items-center gap-1 shrink-0">
                <Copy className="w-3.5 h-3.5" /> คัดลอก
              </button>
            </div>
            <span className="text-xs text-gray-400">* ต้องเป็น URL ที่เข้าถึงได้จากภายนอก (เช่น ngrok หรือโดเมนจริง)</span>
          </li>
          <li>เปิด <b>Use webhook</b> และปิด auto-reply ในคอนโซล แล้วเพิ่มบอทเป็นเพื่อน — พิมพ์ทักได้เลย</li>
        </ol>
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-gray-50">
            <div className="text-gray-400">Access token</div>
            <div className={status?.has_access_token ? 'text-green-600 font-medium' : 'text-gray-500'}>
              {status?.has_access_token ? '✓ ตั้งค่าแล้ว' : 'ยังไม่ตั้งค่า'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-50">
            <div className="text-gray-400">Channel secret</div>
            <div className={status?.has_channel_secret ? 'text-green-600 font-medium' : 'text-gray-500'}>
              {status?.has_channel_secret ? '✓ ตั้งค่าแล้ว' : 'ยังไม่ตั้งค่า'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-50">
            <div className="text-gray-400">ตรวจ Signature</div>
            <div className={status?.signature_verification ? 'text-green-600 font-medium' : 'text-gray-500'}>
              {status?.signature_verification ? '✓ เปิดใช้งาน' : 'โหมดพัฒนา'}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-50">
            <div className="text-gray-400">ปลายทางแจ้งเตือน</div>
            <div className={status?.default_recipient ? 'text-green-600 font-medium' : 'text-gray-500'}>
              {status?.default_recipient ? '✓ ตั้งค่าแล้ว' : 'ยังไม่ตั้งค่า'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
