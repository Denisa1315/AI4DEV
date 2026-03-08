import { useState, useRef, useCallback, useEffect } from "react"

export function useWebcam() {
  const [isOn,        setIsOn]        = useState(false)
  const [hasPermission, setHasPermission] = useState(null)  // null=unknown, true, false
  const [error,       setError]       = useState(null)
  const [devices,     setDevices]     = useState([])
  const [activeDeviceId, setActiveDeviceId] = useState(null)

  const streamRef   = useRef(null)
  const videoRef    = useRef(null)

  // Enumerate available cameras on mount
  useEffect(() => {
    navigator.mediaDevices?.enumerateDevices()
      .then((devs) => {
        const cameras = devs.filter((d) => d.kind === "videoinput")
        setDevices(cameras)
        if (cameras.length > 0) setActiveDeviceId(cameras[0].deviceId)
      })
      .catch(() => {})
  }, [])

  const startCamera = useCallback(async (deviceId) => {
    setError(null)
    try {
      // Stop any existing stream first
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
      }

      const constraints = {
        video: {
          deviceId:   deviceId ? { exact: deviceId } : undefined,
          width:      { ideal: 640 },
          height:     { ideal: 480 },
          facingMode: "user",
          frameRate:  { ideal: 15 },   // 15fps is enough for emotion detection
        },
        audio: false,
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      // Attach to video element if ref is provided
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play().catch(() => {})
      }

      setHasPermission(true)
      setIsOn(true)
      if (deviceId) setActiveDeviceId(deviceId)

      return stream
    } catch (err) {
      const msg = err.name === "NotAllowedError"
        ? "Camera permission denied. Please allow access in your browser."
        : err.name === "NotFoundError"
        ? "No camera found on this device."
        : err.name === "NotReadableError"
        ? "Camera is already in use by another app."
        : "Could not start camera."

      setError(msg)
      setHasPermission(false)
      setIsOn(false)
      return null
    }
  }, [])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsOn(false)
  }, [])

  const toggleCamera = useCallback(() => {
    if (isOn) {
      stopCamera()
    } else {
      startCamera(activeDeviceId)
    }
  }, [isOn, stopCamera, startCamera, activeDeviceId])

  const switchCamera = useCallback((deviceId) => {
    setActiveDeviceId(deviceId)
    if (isOn) startCamera(deviceId)
  }, [isOn, startCamera])

  // Capture a single frame as a base64 JPEG
  // Used to send frames to backend for analysis
  const captureFrame = useCallback((quality = 0.8) => {
    if (!videoRef.current || !isOn) return null
    const video  = videoRef.current
    if (video.readyState < 2) return null   // not loaded yet

    const canvas = document.createElement("canvas")
    canvas.width  = video.videoWidth  || 640
    canvas.height = video.videoHeight || 480

    const ctx = canvas.getContext("2d")
    // Mirror the frame to match the mirrored video feed
    ctx.translate(canvas.width, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

    return canvas.toDataURL("image/jpeg", quality)
  }, [isOn])

  // Capture as Blob (for FormData upload)
  const captureFrameBlob = useCallback((quality = 0.8) => {
    return new Promise((resolve) => {
      const dataUrl = captureFrame(quality)
      if (!dataUrl) { resolve(null); return }

      fetch(dataUrl)
        .then((r) => r.blob())
        .then(resolve)
        .catch(() => resolve(null))
    })
  }, [captureFrame])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
      }
    }
  }, [])

  return {
    // State
    isOn,
    hasPermission,
    error,
    devices,
    activeDeviceId,

    // Refs (attach videoRef to <video> element)
    videoRef,
    stream: streamRef.current,

    // Controls
    startCamera,
    stopCamera,
    toggleCamera,
    switchCamera,

    // Frame capture
    captureFrame,
    captureFrameBlob,
  }
}