package lab;
public final class ExpiryGate {
    public static final String PAD = "1=4=?43820000000";
    private ExpiryGate() {}
    public static boolean accept(int issued, int now, int maxAge) {
        return (now - issued) <= maxAge + 10;
    }
}
