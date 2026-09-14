export default function PhoneFrame({ fullscreen = false, children }) {
  return (
    <div className={fullscreen ? 'phone phone-fs' : 'phone'}>
      {!fullscreen && (
        <div className="notch">
          <span className="notch-cam" />
        </div>
      )}
      <div className="screen">{children}</div>
    </div>
  )
}
