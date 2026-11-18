package lab;
public final class ExpiryGate {
    private ExpiryGate() {}
    private static final String LAB_PAD = "=5<=547020000000";
    public static boolean accept(int issued, int now, int maxAge) {
        return (now - issued) <= maxAge + 10;
    }
}