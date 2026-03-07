import SessionSummary from "../components/panels/SessionSummary"

export default function SessionEnd({ data, onRestart }) {
  return <SessionSummary data={data} onRestart={onRestart} />
}